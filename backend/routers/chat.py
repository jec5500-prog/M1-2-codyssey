# backend/routers/chat.py
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from google.cloud import firestore
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from database import get_db
from models import ChatRequest, ChatResponse, ConversationDetail, ConversationMeta
from routers.data import compute_summary, fetch_points

logger = logging.getLogger("chat")

router = APIRouter(prefix="/api", tags=["chat"])

CONVERSATIONS = "conversations"
MAX_HISTORY_MESSAGES = 20  # 모델에 전달할 최근 대화 수
MAX_STORED_MESSAGES = 200  # 문서 1MB 제한 대비 저장 상한
MAX_TOOL_ROUNDS = 5  # Function Calling 최대 반복 횟수
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_client: Optional[OpenAI] = None


def _get_openai() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="서버에 OPENAI_API_KEY 가 설정되지 않았습니다.",
            )
        _client = OpenAI(api_key=api_key, timeout=60.0, max_retries=2)
    return _client


def _model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------ Function Calling 스키마
TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_data_points",
            "description": (
                "Firestore 에 저장된 시계열 데이터(date, value, memo)를 기간/정렬/개수 조건으로 "
                "조회한다. 특정 날짜나 기간의 원본 값이 필요할 때 사용한다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "조회 시작일 (YYYY-MM-DD). 생략 시 처음부터.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "조회 종료일 (YYYY-MM-DD). 생략 시 끝까지.",
                    },
                    "order": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                        "description": "날짜 정렬. 최근 데이터는 desc. 기본 asc.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "최대 반환 건수 (기본 50, 최대 200).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_summary",
            "description": (
                "지정한 기간의 건수, 평균, 합계, 최소/최대, 최근 추세를 계산해 반환한다. "
                "기간을 생략하면 전체 데이터를 요약한다. 기간별 비교에 유용하다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_extreme_points",
            "description": "값이 가장 높거나 낮은 상위 N개 데이터를 반환한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["highest", "lowest"],
                        "description": "highest=값이 큰 순, lowest=값이 작은 순",
                    },
                    "n": {"type": "integer", "description": "반환 개수 (기본 5, 최대 50)"},
                    "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
                },
                "required": ["mode"],
            },
        },
    },
]

TOOL_LABELS = {
    "query_data_points": "query_data_points",
    "get_data_summary": "get_data_summary",
    "get_extreme_points": "get_extreme_points",
}


def _valid_date(v: Any) -> Optional[str]:
    if v is None or v == "":
        return None
    if isinstance(v, str) and DATE_RE.match(v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            pass
    raise ValueError(f"잘못된 날짜 형식입니다: {v!r} (YYYY-MM-DD 필요)")


def _clamp(v: Any, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """모델이 요청한 도구를 실제로 실행하고 JSON 직렬화 가능한 결과를 반환."""
    try:
        start = _valid_date(args.get("start_date"))
        end = _valid_date(args.get("end_date"))

        if name == "query_data_points":
            limit = _clamp(args.get("limit"), 50, 1, 200)
            order = "desc" if args.get("order") == "desc" else "asc"
            pts = fetch_points(start, end, limit, descending=(order == "desc"))
            return {
                "count": len(pts),
                "points": [
                    {"date": p["date"], "value": p["value"], "memo": p["memo"]} for p in pts
                ],
            }

        if name == "get_data_summary":
            return compute_summary(fetch_points(start, end))

        if name == "get_extreme_points":
            n = _clamp(args.get("n"), 5, 1, 50)
            mode = args.get("mode")
            if mode not in ("highest", "lowest"):
                return {"error": "mode 는 highest 또는 lowest 여야 합니다."}
            pts = fetch_points(start, end)
            pts.sort(key=lambda p: p["value"], reverse=(mode == "highest"))
            return {
                "mode": mode,
                "points": [
                    {"date": p["date"], "value": p["value"], "memo": p["memo"]}
                    for p in pts[:n]
                ],
            }

        return {"error": f"알 수 없는 도구: {name}"}
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Tool execution failed: %s", name)
        return {"error": f"도구 실행 중 오류: {exc}"}


def build_system_prompt(summary: Dict[str, Any]) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return (
        "당신은 사용자의 시계열 데이터(date, value, memo)를 분석해 주는 친절한 AI 어시스턴트입니다.\n"
        f"오늘 날짜는 {today} 입니다.\n"
        "규칙:\n"
        "1) 항상 사용자가 쓴 언어(기본 한국어)로 간결하고 명확하게 답변하세요.\n"
        "2) 아래 '전체 데이터 요약'을 우선 활용하되, 특정 기간의 원본 값·기간 비교·최고/최저 등 "
        "더 자세한 정보가 필요하면 제공된 도구(function)를 호출해 실제 데이터를 조회하세요.\n"
        "3) 데이터에 없는 수치를 절대 지어내지 마세요. 데이터가 없으면 없다고 말하세요.\n"
        "4) 수치를 인용할 때는 날짜와 함께 제시하고, 필요하면 간단한 해석/인사이트를 덧붙이세요.\n\n"
        "[전체 데이터 요약 (JSON)]\n"
        f"{json.dumps(summary, ensure_ascii=False)}"
    )


# ------------------------------------------------------------------ 대화 저장소
def _conv_col():
    return get_db().collection(CONVERSATIONS)


def _meta_from_doc(doc) -> Dict[str, Any]:
    d = doc.to_dict() or {}
    return {
        "id": doc.id,
        "title": d.get("title", "새 대화"),
        "created_at": d.get("created_at", ""),
        "updated_at": d.get("updated_at", ""),
        "message_count": len(d.get("messages", [])),
    }


def _make_title(message: str) -> str:
    one_line = " ".join(message.split())
    return one_line[:40] + ("…" if len(one_line) > 40 else "")


def _openai_error_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, AuthenticationError):
        return HTTPException(502, "OpenAI 인증에 실패했습니다. API 키를 확인하세요.")
    if isinstance(exc, RateLimitError):
        return HTTPException(429, "OpenAI 요청 한도를 초과했습니다. 잠시 후 다시 시도하세요.")
    if isinstance(exc, APITimeoutError):
        return HTTPException(504, "OpenAI 응답 시간이 초과되었습니다.")
    if isinstance(exc, APIConnectionError):
        return HTTPException(502, "OpenAI 서버에 연결할 수 없습니다.")
    if isinstance(exc, APIError):
        return HTTPException(502, f"OpenAI API 오류: {getattr(exc, 'message', str(exc))}")
    return HTTPException(500, "알 수 없는 오류가 발생했습니다.")


# ------------------------------------------------------------------ 엔드포인트
@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    client = _get_openai()

    # 1) 대화 로드 또는 생성
    conv_ref = None
    stored: List[Dict[str, Any]] = []
    title = _make_title(req.message)
    created_at = _now_iso()

    if req.conversation_id:
        conv_ref = _conv_col().document(req.conversation_id)
        snap = conv_ref.get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        cdata = snap.to_dict() or {}
        stored = list(cdata.get("messages", []))
        title = cdata.get("title", title)
        created_at = cdata.get("created_at", created_at)
    else:
        conv_ref = _conv_col().document()

    # 2) /summary 데이터를 system 프롬프트로 주입
    summary = compute_summary(fetch_points())
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": build_system_prompt(summary)}
    ]
    for m in stored[-MAX_HISTORY_MESSAGES:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": req.message})

    # 3) OpenAI 호출 + Function Calling 루프
    tools_used: List[str] = []
    reply: Optional[str] = None
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            completion = client.chat.completions.create(
                model=_model(),
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            msg = completion.choices[0].message

            if not msg.tool_calls:
                reply = msg.content or ""
                break

            # assistant 의 tool_calls 메시지를 대화에 추가
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )

            # 각 도구 실행 후 role=tool 메시지로 결과 전달
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                    if not isinstance(args, dict):
                        args = {}
                except json.JSONDecodeError:
                    args = {}
                result = execute_tool(tc.function.name, args)
                label = TOOL_LABELS.get(tc.function.name, tc.function.name)
                if label not in tools_used:
                    tools_used.append(label)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

        if reply is None:
            # 도구 호출 한도 초과 → 도구 없이 최종 답변 강제
            completion = client.chat.completions.create(model=_model(), messages=messages)
            reply = completion.choices[0].message.content or ""
    except HTTPException:
        raise
    except (
        AuthenticationError,
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        APIError,
    ) as exc:
        logger.error("OpenAI error: %s", exc)
        raise _openai_error_to_http(exc) from exc

    if not reply.strip():
        reply = "죄송합니다, 응답을 생성하지 못했습니다. 다시 한 번 질문해 주세요."

    # 4) Firestore 에 자동 저장
    now = _now_iso()
    stored.append({"role": "user", "content": req.message, "timestamp": now, "tools_used": []})
    stored.append(
        {"role": "assistant", "content": reply, "timestamp": _now_iso(), "tools_used": tools_used}
    )
    stored = stored[-MAX_STORED_MESSAGES:]

    conv_ref.set(
        {
            "title": title,
            "created_at": created_at,
            "updated_at": _now_iso(),
            "messages": stored,
        }
    )

    return ChatResponse(
        conversation_id=conv_ref.id, reply=reply, tool_calls_used=tools_used
    )


@router.get("/conversations", response_model=List[ConversationMeta])
def list_conversations(limit: int = 50):
    limit = max(1, min(limit, 200))
    docs = (
        _conv_col()
        .order_by("updated_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [_meta_from_doc(d) for d in docs]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str):
    snap = _conv_col().document(conversation_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    d = snap.to_dict() or {}
    meta = _meta_from_doc(snap)
    messages = [
        {
            "role": m.get("role", "assistant"),
            "content": m.get("content", ""),
            "timestamp": m.get("timestamp", ""),
            "tools_used": m.get("tools_used", []),
        }
        for m in d.get("messages", [])
    ]
    return {**meta, "messages": messages}


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str):
    ref = _conv_col().document(conversation_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    ref.delete()
    return None