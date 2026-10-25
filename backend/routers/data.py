# backend/routers/data.py
import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from database import get_db
from models import DataPoint, DataPointCreate, DataPointUpdate, Summary

logger = logging.getLogger("data")

router = APIRouter(prefix="/api/data", tags=["data"])

COLLECTION = "data_points"
TREND_WINDOW = 7
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


# ------------------------------------------------------------------ 헬퍼
def _col():
    return get_db().collection(COLLECTION)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _doc_to_point(doc) -> Dict[str, Any]:
    d = doc.to_dict() or {}
    return {
        "id": doc.id,
        "date": d.get("date", ""),
        "value": float(d.get("value", 0) or 0),
        "memo": d.get("memo", "") or "",
    }


def fetch_points(
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
    descending: bool = False,
) -> List[Dict[str, Any]]:
    """기간 필터/정렬/개수 제한을 적용해 데이터 포인트 목록을 반환 (챗 도구에서도 재사용)."""
    query = _col()
    if start:
        query = query.where(filter=FieldFilter("date", ">=", start))
    if end:
        query = query.where(filter=FieldFilter("date", "<=", end))
    query = query.order_by(
        "date",
        direction=firestore.Query.DESCENDING if descending else firestore.Query.ASCENDING,
    )
    if limit:
        query = query.limit(limit)
    return [_doc_to_point(d) for d in query.stream()]


def _compute_trend(values: List[float]) -> Dict[str, Any]:
    window = min(len(values), TREND_WINDOW)
    if window < 2:
        return {
            "direction": "insufficient",
            "label": "데이터 부족 (2건 이상 필요)",
            "window": window,
            "slope": None,
            "change_percent": None,
            "recent_average": values[-1] if values else None,
        }

    recent = values[-window:]
    mean_x = (window - 1) / 2
    mean_y = sum(recent) / window
    num = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(recent))
    den = sum((x - mean_x) ** 2 for x in range(window))
    slope = num / den if den else 0.0

    base = abs(mean_y)
    if base > 0:
        rel = slope / base
    else:
        rel = 1.0 if slope > 0 else (-1.0 if slope < 0 else 0.0)

    if rel > 0.01:
        direction, label = "up", "상승 추세"
    elif rel < -0.01:
        direction, label = "down", "하락 추세"
    else:
        direction, label = "flat", "보합 (큰 변화 없음)"

    first, last = recent[0], recent[-1]
    change_percent = ((last - first) / abs(first) * 100) if first != 0 else None

    return {
        "direction": direction,
        "label": label,
        "window": window,
        "slope": round(slope, 4),
        "change_percent": round(change_percent, 2) if change_percent is not None else None,
        "recent_average": round(mean_y, 4),
    }


def compute_summary(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """건수 / 평균 / 최소·최대 / 최근 추세 요약 (챗 시스템 프롬프트에서도 재사용)."""
    pts = sorted(points, key=lambda p: p["date"])
    n = len(pts)
    if n == 0:
        return {
            "count": 0,
            "average": None,
            "total": None,
            "minimum": None,
            "maximum": None,
            "latest": None,
            "first_date": None,
            "last_date": None,
            "trend": _compute_trend([]),
        }

    values = [p["value"] for p in pts]
    total = sum(values)
    min_p = min(pts, key=lambda p: p["value"])
    max_p = max(pts, key=lambda p: p["value"])

    def ref(p):
        return {"date": p["date"], "value": p["value"], "memo": p.get("memo", "")}

    return {
        "count": n,
        "average": round(total / n, 4),
        "total": round(total, 4),
        "minimum": ref(min_p),
        "maximum": ref(max_p),
        "latest": ref(pts[-1]),
        "first_date": pts[0]["date"],
        "last_date": pts[-1]["date"],
        "trend": _compute_trend(values),
    }


def _csv_safe(text: str) -> str:
    """CSV 수식 인젝션 방지."""
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


# ------------------------------------------------------------------ 엔드포인트
@router.post("", response_model=DataPoint, status_code=201)
def create_point(payload: DataPointCreate):
    ref = _col().document()
    body = payload.model_dump()
    ref.set({**body, "created_at": _now_iso(), "updated_at": _now_iso()})
    return {"id": ref.id, **body}


@router.get("", response_model=List[DataPoint])
def list_points(
    start: Optional[str] = Query(None, pattern=DATE_PATTERN, description="시작일"),
    end: Optional[str] = Query(None, pattern=DATE_PATTERN, description="종료일"),
    limit: int = Query(500, ge=1, le=2000),
    order: str = Query("asc", pattern="^(asc|desc)$"),
):
    return fetch_points(start, end, limit, descending=(order == "desc"))


@router.get("/summary", response_model=Summary)
def get_summary(
    start: Optional[str] = Query(None, pattern=DATE_PATTERN),
    end: Optional[str] = Query(None, pattern=DATE_PATTERN),
):
    return compute_summary(fetch_points(start, end))


@router.get("/export/csv")
def export_csv():
    points = fetch_points()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "value", "memo"])
    for p in points:
        writer.writerow([p["date"], p["value"], _csv_safe(p["memo"])])

    # UTF-8 BOM: Excel 에서 한글이 깨지지 않도록
    content = "\ufeff" + buf.getvalue()
    filename = f"data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{point_id}", response_model=DataPoint)
def get_point(point_id: str):
    snap = _col().document(point_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    return _doc_to_point(snap)


@router.put("/{point_id}", response_model=DataPoint)
def update_point(point_id: str, payload: DataPointUpdate):
    ref = _col().document(point_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="수정할 필드가 없습니다.")

    updates["updated_at"] = _now_iso()
    ref.update(updates)
    return _doc_to_point(ref.get())


@router.delete("/{point_id}", status_code=204)
def delete_point(point_id: str):
    ref = _col().document(point_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    ref.delete()
    return None