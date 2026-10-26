# AI 비서 완성 Implementation Plan

> 2026-10-25 승인 시점의 실행 계획 기록입니다. 현재 완료 상태는 ../mission-audit-2026-10-27.md를 확인하세요.

**Goal:** 기존 AI 비서의 필수·보너스 요건을 검증 가능한 상태로 완성하고 2026-10-27까지 제출 준비를 끝낸다.

**Architecture:** 기존 FastAPI·Firestore·OpenAI 및 바닐라 UI를 유지한다. 라우터의 공용 요약/대화/AI 로직을 서비스로 분리하고, MCP stdio 어댑터는 동일 배포 API를 호출한다. 기존 Firebase와 Render를 재사용한다.

**Tech Stack:** Python>=3.10, FastAPI, uvicorn, Pydantic v2, firebase-admin, openai Python SDK, python-dotenv, HTML/CSS/JavaScript, Chart.js, Render, Vercel, optional 공식 MCP Python SDK.

**Spec:** [작업지시서·설계 승인안](2026-10-25-work-order.md), [현황·증거](2026-10-25-current-state.md).

**상태:** 2026-10-25 사용자 승인, 개발 진행 중. 아래 명령·경로는 실행 계획이며 실행 결과가 아니다. 파일 경로는 승인 후 `C:/Users/josep/Documents/ChatGPT/M1-2 Codyssey/app/` 기준이다. 체크박스는 구현 완료 때만 바꾼다.

**2026-10-25 배포 경로 변경:** 사용자 요청에 따라 Vercel CLI 로그인·CLI 검증은 완료 조건에서 제외한다. Vercel 대시보드에서 프론트를 배포하고 공개 URL의 실제 화면, Render API 연결, 정확한 CORS origin으로 A7을 판정한다. GitHub 앱 접근 범위 변경이 필요하면 해당 저장소만 대상으로 검토한다.

**실행 결과:** 기능별 통과 근거와 공개 배포 주소는 [인수 검사표](../app/docs/acceptance.md)에 모은다. 이 문서의 체크박스는 승인 당시의 작업 목록이며 실제 완료 판정은 인수 검사표를 따른다.

## Global Constraints

- 백엔드는 FastAPI, DB는 Firebase Firestore, AI는 GPT API, 프론트는 HTML/CSS/JavaScript(프레임워크 금지).
- 백엔드는 기존 Render srv-dber447b9u1s73alsrmg, 프론트는 Vercel.
- data/conversations 컬렉션, 유효한 시계열 데이터 최소 100건.
- API 키/서비스 계정 키는 환경변수에만 보관. 원본 .env, 로그, 아티팩트에서 비밀을 노출하지 않음.
- 필수 API 10개와 보너스 전체, README 및 화면 증빙을 함께 검수.
- 2026-10-27까지 제출 가능한 상태. 10월 28일에 예정된 구현 작업 없음.
- 사용자 계획 승인 전 제품 코드·서비스 설정·DB 데이터 변경 금지.

## Review Focus

1. 빈 데이터·한 건·0/음수·중복 날짜의 통계 일관성 → Task 2/3 테스트.
2. 존재하지 않는 날짜·뒤집힌 기간·NaN/Infinity가 저장/조회에 유입 → Task 2/3 검증 테스트.
3. GPT 지연·429·도구 오류·토큰/시간 예산 초과 → Task 4 대역 테스트 및 제한된 실키 확인.
4. 동일 대화 동시 전송·삭제 경쟁·용량 초과가 이력을 덮거나 자름 → Task 3/4/5 회귀 검사.
5. 설정된 URL 누락·CORS 불일치·Render 콜드스타트·차트 CDN 실패 → Task 1/5/7 설정 및 브라우저 검사.

## 파일 구성

| 작업 | 생성·수정 예정 파일과 책임 |
|---|---|
| 기반 | `.gitignore`, `.vscode/settings.json`, `.vscode/launch.json`, `.vscode/tasks.json`, `backend/requirements-dev.txt`, `backend/requirements.lock.txt`, `backend/.python-version`, `render.yaml` |
| 설정/검증 | `backend/settings.py`, `backend/main.py`, `backend/models.py`, `backend/.env.example`, `backend/database.py` |
| 데이터 | `backend/services/data_summary.py`, `backend/routers/data.py`, `datasets/seoul-temperature.csv`, `datasets/README.md`, `scripts/import_data.py` |
| 대화 | `backend/services/conversations.py`, `backend/routers/chat.py`, `backend/models.py` |
| AI | `backend/services/ai_chat.py`, `backend/services/tools.py`, `backend/routers/chat.py` |
| 화면 | 기존 `frontend/app.js`, `index.html`, `style.css`, `config.js`, `vercel.json`, 새 `frontend/scripts/build-config.mjs` |
| MCP | `backend/requirements-mcp.txt`, `integrations/mcp/server.py`, `scripts/verify_mcp.py` |
| 증빙 | `README.md`, `firestore.rules`, `docs/screenshots/`, `docs/acceptance.md`, `docs/test-results/` |
| 테스트 | `backend/tests/test_settings.py`, `test_data.py`, `test_summary.py`, `test_conversations.py`, `test_chat.py`, `test_import.py`, `tests/frontend/*.test.mjs`, `tests/mcp/` |

이름/경로 변경이 필요하면 먼저 계획을 갱신한다. 테스트 전용 의존성은 본체에서 분리하고 검증한 버전을 기록한다. 원본의 빈 README.md 폴더는 삭제하지 않고 보존하며 새 작업 사본에는 README 파일을 만든다.

## Task 1: 작업 기준과 배포 경로 복구 — 2~3시간

**Files:** 기반 파일, backend/settings.py, main.py, .env.example, frontend/scripts/build-config.mjs, vercel.json.

**Interfaces:** settings의 `allowed_origins: list[str]`, `openai_model: str`, `chat_deadline_seconds: int`를 라우터/서비스가 소비. 프론트 `window.APP_CONFIG.API_BASE_URL: string` 유지.

- [ ] 기존 저장소를 app/에 clone하고 remote/main SHA를 원본과 대조. `codex/ai-assistant-completion` 브랜치 생성. 기존 변경 보존.
- [ ] 새 venv와 테스트 도구 구성. 원본 비밀 파일은 gitignored 경로에서만 사용. VS Code 인터프리터·API/프론트 실행 task 설정.
- [ ] 실패 테스트: ALLOWED_ORIGINS만 설정해도 적용, 이전 CORS_ORIGINS 호환, 충돌 시 명시적 실패, 운영 API_BASE_URL 누락/localhost/잘못된 URL 빌드 거절.
- [ ] 테스트 실패 확인 후 설정 구현. load_dotenv가 배포 주입값을 덮지 않도록 수정. URL 설정 생성은 JSON.stringify 사용.
- [ ] 기존 Render 설정을 백업 기록하고 Root Directory=backend, 현재 build/start 명령 유지, health path=/health, 지원 Python 3.13 패치 고정. 최초 경로 복구는 현재 원격 main의 2e9675f를 기준으로 한다. 설정 저장은 재배포를 유발할 수 있으며, 로컬 수정 코드의 배포는 Task 7에서 검증 커밋을 원격에 반영하고 대상을 확정한 뒤 진행한다.
- [ ] 실행: `python -m pytest backend/tests/test_settings.py -q`, `node --test tests/frontend/config.test.mjs`, `python -m pip check`. 기대: 실패 0, 의존성 충돌 없음.
- [ ] 확인된 변경만 커밋. 기존 Render 서비스/URL 유지. 이 단계의 기동 성공을 DB/GPT 통합 성공으로 표시하지 않음.

## Task 2: 출처 있는 데이터와 요약·CRUD — 3~4시간

**Files:** 데이터 파일, models.py, routers/data.py, data_summary.py, test_data.py, test_summary.py, test_import.py.

**Interfaces:** `compute_summary(points: list[dict]) -> dict`는 기존 Summary 응답을 유지. `fetch_points(start=None,end=None,limit=None,descending=False) -> list[dict]` 인터페이스 유지. 적재기는 CSV를 검증하고 결정적 문서 ID로 업서트.

- [ ] 승인된 서울 일별 평균기온 122건을 출처에서 수집하고 출처·단위·기간·재분석 데이터임을 기록. 날짜/결측/중복/유한수를 검증.
- [ ] 실패 테스트: 0건/1건/상승/하락/보합/0/음수/중복날짜, 비유한 수 생성·수정 422, 실제 없는 조회 날짜와 start>end 422, 없는 ID 404.
- [ ] 실패 확인 후 공용 요약 서비스 분리, 컬렉션을 data로 정합화. 존재하는 데이터가 있으면 삭제 없이 보존·대조.
- [ ] 데이터 CRUD와 summary/export가 같은 검증·조회 규칙을 사용하도록 연결. 프론트 2000건 제한은 조회 범위를 표시하거나 같은 범위로 맞춤.
- [ ] 적재기를 두 번 실행해도 건수가 늘지 않는지 테스트. 실제 적재 시 대상 프로젝트가 m1-2-cody인지 먼저 확인.
- [ ] 실행: `python -m pytest backend/tests/test_data.py backend/tests/test_summary.py backend/tests/test_import.py -q`. 기대: 모든 통과.
- [ ] 실제 data count>=100 및 원본 CSV로 독립 계산한 count/평균/최소/최대/기간과 API 결과 대조 후 커밋.

## Task 3: 대화 수동/자동 저장·불러오기 — 2~3시간

**Files:** models.py, services/conversations.py, routers/chat.py, test_conversations.py, firestore.rules.

**Interfaces:** `save_conversation(title: str|None, messages: list[dict]) -> ConversationDetail`, `append_turn(conversation_id: str|None, user: str, assistant: str, tools_used: list[str]) -> str`. 목록은 메타데이터, GET 상세는 messages 포함. 수동 POST 계약은 작업지시서 §5.

- [ ] 실패 테스트: 수동 저장 201→상세 동일 내용, 목록/삭제 204/없는 ID404, system 역할·빈 배열·공백 content422, 200개/900000바이트 초과 시 기존 이력 보존.
- [ ] 실패 확인 후 POST conversations 및 공용 저장 서비스 구현. 오래된 메시지 silent truncation 제거. 메시지별 content 최대 4000자, role 제한, 서버 timestamp 생성.
- [ ] 동시 두 append가 둘 다 보존되고, 전송 중 삭제된 대화가 다시 생성되지 않는지 저장소 대역/통합 테스트. SDK/LLM 호출은 Firestore 트랜잭션 밖에서 실행.
- [ ] Firebase 클라이언트 접근 규칙을 거절 정책으로 관리. Admin SDK 읽기/쓰기와 클라이언트 규칙을 구분해 README에 설명.
- [ ] 실행: `python -m pytest backend/tests/test_conversations.py -q`. 실제 저장/조회는 명시적 시연 대화로 확인. 기본 데이터 삭제는 하지 않음.
- [ ] 통과 후 커밋.

## Task 4: AI 컨텍스트·도구 호출·비용 제한 — 3~4시간

**Files:** services/ai_chat.py, services/tools.py, routers/chat.py, settings.py, test_chat.py.

**Interfaces:** `build_system_prompt(summary: dict) -> str`, `execute_tool(name: str,args: dict) -> dict`, `run_chat(message: str, conversation_id: str|None) -> ChatResponse`. 외부 응답 계약 유지.

- [ ] 실패 테스트: 요약이 system에 포함, 최근20개 이력만 전달, 정상 답변 자동저장, 데이터0건 응답 안내, 미등록 도구/잘못된 인자/도구 오류, SDK401·429·지연 예외의 HTTP 변환.
- [ ] 실패 테스트: 각 생성 호출에 출력600토큰 상한, 라운드3회·라운드당3도구, 전체90초, 호출20초/남은예산 이내, 자동재시도0, chat IP분당6회 초과429. 상한 도달 후 무한 재시도/이력 유실 없음.
- [ ] 실패 확인 후 AI/도구 로직 분리. 원시 데이터·memo는 신뢰할 수 없는 자료로 구분하고 모델에 데이터 밖 수치 추측 금지 지시. 내부 예외/키 노출 차단.
- [ ] 실행: `python -m pytest backend/tests/test_chat.py -q`. 모든 외부 GPT 응답은 대역 사용, 실제 키 불필요.
- [ ] 승인된 실키 질문 최대5개로 전체요약·최근추세·기간비교·최고5개·대화후속 확인. 도구 호출 로그는 도구명/인자/반환근거만 기록. 실패 시 인증/잔액/데이터/코드 원인 분리.
- [ ] 실제 답변 수치와 API 통계를 대조하고 자동 저장/재조회 확인 후 커밋.

## Task 5: 프론트 실제 연결·경쟁 처리·보너스 UX — 2~3시간

**Files:** frontend/app.js, index.html, style.css, tests/frontend/*.test.mjs.

**Interfaces:** 기존 chat/data/conversation 응답 유지. 화면의 대화는 chat 자동저장을 사용한다. 수동 POST 저장은 Task 3의 API·Swagger 시연으로 별도 검증한다.

- [ ] 실패 검사: 느린 이전 대화 조회가 나중 선택한 화면을 덮지 않음, 전송 중 삭제 충돌, 저장/조회 실패 시 거짓 성공 표시 없음, 비유한 수 전송 차단.
- [ ] 확인 후 요청 식별자·상태 처리 구현. chat 자동 저장 성공과 불러오기 결과를 명확하게 안내하고 이미 저장된 대화를 중복 생성하지 않음.
- [ ] `node --check frontend/app.js`, `node --test tests/frontend/*.test.mjs` 통과.
- [ ] 실제 브라우저에서 추가→목록/요약갱신→수정→삭제, 채팅 로딩→응답→새로고침→불러오기, CSV 한글·수식문자 처리, 그래프, 테마 유지 확인.
- [ ] 데스크톱·모바일 폭, 한글 IME Enter, 차트 CDN 실패, 서버 대기 배너/실패 안내 검수 후 커밋.

## Task 6: MCP 외부 클라이언트 연동 — 2~4시간, 상한 도달 시 보고

**Files:** integrations/mcp/server.py, backend/requirements-mcp.txt, scripts/verify_mcp.py, tests/mcp/.

**Interfaces:** stdio `get_data_summary(start_date?:str,end_date?:str)`와 `query_data_points(start_date?:str,end_date?:str,limit?:int,order?:str)` 도구. 기존 Render GET API로 매핑, 비밀 키 전달 없음.

- [ ] 공식 SDK 안정 버전을 확인·고정하고 optional 환경에 설치. 가짜 API로 도구 스키마/인자 매핑/timeout/오류 테스트를 먼저 실패시킴.
- [ ] 확인 후 stdio 서버 구현. stdout에는 프로토콜 메시지만 출력, 로그는 stderr.
- [ ] SDK 클라이언트가 별도 프로세스 서버와 handshake→list_tools→call_tool을 수행하는 통합 테스트. 단순 Python 함수 직접 호출을 MCP 성공으로 세지 않음.
- [ ] 실제 배포 Render API를 대상으로 같은 호출 실행, 반환 count/평균을 직접 API와 대조. 입출력 증거를 비밀 없는 JSON으로 저장.
- [ ] README에 독립 클라이언트 실행법과 ‘질문→도구선택→MCP→API→통계’ 흐름, 근거를 기록 후 커밋.

## Task 7: 배포·최종 제출 패키지 — 4~5시간, 일부 앞 단계와 병행

**Files:** render.yaml, frontend/vercel.json, README.md, docs/acceptance.md, docs/screenshots/, docs/test-results/.

**Interfaces:** 기존 Render URL 및 새/기존 Vercel 프론트 URL, API_BASE_URL과 ALLOWED_ORIGINS 상호 일치.

- [ ] GitHub 비밀정보·추적 파일 검토 후 작업 브랜치 푸시/초안 PR. 승인된 작업 방식으로 테스트된 커밋을 배포 대상으로 사용. main 병합이나 자동 배포 전 정확한 대상 확인.
- [ ] 기존 Render 서비스에서 backend 경로·Python·환경변수·health를 검증하고 배포. root, health, docs, openapi, data/summary 실제 HTTPS 확인.
- [ ] Vercel 대시보드에서 저장소 연결 또는 파일 업로드로 프론트를 배포. Root Directory=frontend, API_BASE_URL 설정을 확인하고 프론트 URL 확정. CLI 인증·검증은 요구하지 않음.
- [ ] Render ALLOWED_ORIGINS에 정확한 Vercel origin 적용. 프리뷰 전체 도메인 wildcard 허용은 하지 않음. CORS preflight와 브라우저 네트워크 확인.
- [ ] 실제 브라우저→Render→Firestore/GPT→응답→저장→불러오기 전 흐름 검수. 무료 서비스 재시작 지연과 에러 안내 확인.
- [ ] README 필수 항목, 데이터 출처/단위, 서비스 구조 설명, 환경변수, 로컬실행, 도구/MCP 근거를 작성.
- [ ] 필수 스크린샷: ①요약+질문/답변 ②CRUD 결과 ③대화 불러오기. 추가로 그래프/CSV/테마/MCP 증거 연결.
- [ ] 전체 pytest/JS/의존성 검사 후 docs/acceptance.md의 A1~A10/B1~B3 각각 근거 링크 기재. 실패가 남으면 완료 선언하지 않음.
- [ ] 10월27일까지 최종 커밋/PR·배포 URL·README·화면·검사 결과 묶음 전달. 제출 플랫폼의 최종 제출 조작은 별도 사용자 요청에 따라 수행.

## 계획 자체 검토

필수 API10개→Task2/3/4, 데이터/분석→Task2, 프론트→Task5, 환경/보안→Task1/3/4/7, Render/Vercel·README/화면→Task7, Function Calling→Task4, MCP→Task6, 지표/그래프/CSV/테마→Task2/5에 연결했다. 독립 설계 검토자는 정확한 제출 마감 시각만 추가 변수로 지적했고, 사용자의 ‘27일까지 준비’ 지시를 반영해 28일 개발 의존성을 제거했다.

총 단계별 작업량은 18~26시간으로 추정한다. 실제 첫 기동/실키 확인 후 잔여 예상치를 갱신한다. 납기 확정 약속으로 해석하지 않는다. 단계 완료마다 결과·잔여 문제·다음 단계와 시간 영향을 보고한다.
