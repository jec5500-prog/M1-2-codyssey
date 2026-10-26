# 원본 미션·승인 계획 대조 (2026-10-27 KST)

대조 기준은 사용자가 제공한 `AI Agent 개발 나만의 AI 비서 구축_261025.txt`의 **기능·기술·제약 요건**과 10월 25일 승인한 작업지시서/구현계획이다. 첨부 문서의 서술은 요구사항 자료로만 읽었고, 이 파일은 현재 코드와 실서비스를 다시 검사한 결과다. 공식 제출 마감은 10월 28일, 사용자가 정한 내부 준비 완료일은 10월 27일이다.

| 원본 미션 요구 | 구현 위치 | 10/27 재검증과 판정 |
|---|---|---|
| Python 3.10+, venv, 필수 5패키지 | `backend/requirements.txt`, `.python-version`, `requirements.lock.txt`, README | **충족(검증 환경 3.13.14)**: venv·필수 패키지 설치 상태 및 `pip check` 통과. 3.10 자체 실행은 별도 검증하지 않음 |
| 관심 있는 시계열 데이터 100점 이상, 기간·통계·추세 | `datasets/`, `services/data_summary.py` | **충족**: 서울 일평균기온 122일, Open-Meteo ERA5 재분석·단위·출처 명시. 실 API count/평균과 전체 행 독립 계산 일치 |
| FastAPI 라우터/서비스 분리, Pydantic 검증, CORS, Swagger | `backend/main.py`, `routers/`, `services/`, `models.py`, `settings.py` | **충족**: `/docs`·OpenAPI 200, 잘못된 날짜/비유한 수 422, Vercel origin OPTIONS 허용 확인 |
| Firestore `data`·`conversations`, 서비스 계정 환경변수 | `database.py`, `firestore.rules`, `.env.example` | **충족**: 실제 Firestore 122건·대화 재조회. 키는 Git 비추적 환경변수로 관리; 클라이언트 직접 접근 차단 |
| 데이터 API 5개 및 CRUD 화면 | `routers/data.py`, `frontend/app.js` | **충족**: Render에서 추가/조회/수정/삭제/요약, 삭제 204·없는 ID 404. 임시 점검 데이터 정리 |
| 대화 POST/GET/DELETE와 상세 불러오기 | `routers/chat.py`, `services/conversations.py`, `frontend/app.js` | **충족**: 수동 저장 201, 목록·상세 복원, 삭제 204, AI 자동 저장·복원 |
| 최신 데이터 요약을 GPT 시스템 프롬프트에 주입, 로딩 UI | `services/ai_chat.py`, `frontend/app.js` | **충족**: 단위 테스트에서 시스템 메시지/저장 검사, 10/25 실제 GPT 답변·저장·재조회 증거. 10/27 지정 작업 폴더의 새 GPT 호출도 HTTP 200, 122건·평균 25.12℃ 답변, 자동 저장·재조회·검사 대화 삭제 확인 |
| 바닐라 HTML/CSS/JS 채팅·데이터·대화·요약 | `frontend/index.html`, `style.css`, `app.js` | **충족**: 프레임워크 없이 구현, 로그인된 Vercel 브라우저에서 저장된 GPT 답변과 목록 복원 확인 |
| Render 백엔드, Vercel 프론트, README와 화면 3종 | `render.yaml`, `frontend/vercel.json`, README, `docs/screenshots/` | **조건부**: Render/API/Swagger는 외부 접속 가능. Vercel은 Ready이고 팀 로그인 시 동작하지만 `Require Log In: All Deployments`로 비로그인자는 앱을 볼 수 없음. 사용자가 심사 시 본인 로그인 세션으로 시연하기로 결정. README에 이를 명시 |
| 키 비노출·입력검증·예외·비용 제한 | `settings.py`, `models.py`, `services/ai_chat.py`, `.gitignore` | **충족(코드/회귀 범위)**: 키 추적 없음, 날짜/공백/유한수·크기 검증, GPT 90초·600토큰·도구/속도 제한. 공개 시연에는 개인 정보 입력 금지 |
| 보너스: GPT Function Calling | `services/tools.py`, `ai_chat.py` | **충족**: 실제 질문에서 `get_data_summary` 호출 및 기간별 API 수치와 답변 대조 |
| 보너스: 별도 MCP 또는 GPT Actions | `integrations/mcp/server.py`, `scripts/verify_mcp.py` | **충족**: 별도 stdio 서버/클라이언트 handshake→tool list→호출, 10/27 Render API count 122·평균 일치 |
| 보너스: 추가 지표·그래프·내보내기·다크 모드 | `data_summary.py`, `routers/data.py`, `frontend/` | **충족**: 합계/최근 평균, Chart.js 선 그래프, 122행 UTF-8 BOM CSV, 다크 모드 화면 |

## 승인 계획의 진행 상태

| 단계 | 현재 상태 |
|---|---|
| 1. 작업 사본·설정·Render 복구 | 완료. GitHub 브랜치/초안 PR, VS Code 설정, Render 기동과 설정 검사 |
| 2. 데이터·요약·CRUD | 완료. 출처 있는 122건, 결정적 적재, 실제 CRUD/통계 대조 |
| 3. 수동/자동 대화 저장 | 완료. Firestore 원자 갱신과 이력 보존·재조회 |
| 4. AI 컨텍스트·도구·비용 상한 | 완료. 10/25 Function Calling과 10/27 새 GPT 응답·자동 저장을 각각 실제 호출로 검증 |
| 5. 프론트·보너스 UX | 저장소 구현·화면 검증 완료. 현재 Vercel 배포본에는 그래프 x축 날짜 표시의 이전 콜백이 남아 있어 최신 정적 파일 재배포 필요 |
| 6. MCP 외부 채널 | 완료. 10/27 독립 클라이언트 실 API 재검증 |
| 7. 배포·제출 패키지 | **조건부 완료**. 문서·화면·실서비스 검사는 준비됨. Vercel의 최신 파일 재배포와 보호된 접근에서의 재검증이 남음. 비로그인 접근은 사용자 선택에 따라 차단 상태, GitHub `main`에는 병합하지 않음 |

## 검증 증거와 남은 제한

- 10/27 로컬 회귀: Python 64개, Node 8개 통과, `pip check` 정상, JS 문법 검사 통과. Windows 테스트 클라이언트의 로컬 socketpair가 샌드박스 안에서 멈춰 동일 명령을 허용된 로컬 환경에서 실행해 완료했다.
- 10/27 Render: [API 15항목](test-results/api-live.json) 통과·임시 레코드 제거, [MCP 실 API](test-results/mcp-live.json) count 122 일치. 프론트 origin의 CORS preflight 200 및 정확한 `Access-Control-Allow-Origin` 확인.
- 실제 Function Calling은 10/25 [도구 호출·저장·통계 대조](test-results/live-chat-current.json)로 확인했다. 10/27 지정 작업 폴더의 로컬 API에서 [새 GPT 질문·자동 저장·재조회·검사 대화 삭제](test-results/desktop-migration-chat.json)를 확인했다. 이 질문은 시스템 요약으로 답했고 별도 도구 호출은 없었다.
- Vercel은 GitHub 연결 없이 Drop to Deploy로 업로드했다. 업로드용 최신 4개 파일은 Git 비추적 `.deploy/vercel/`에 모았고 README에 환경변수로 재생성하는 명령을 기록했다. 로그인된 [Vercel 배포 Source 화면](screenshots/vercel-source-drift.jpg)에서 `app.js` 584행은 `callback: (_value, index) => labels[index]?.slice(5) || ''`이고 저장소 최신본은 `callback: value => labels[value]?.slice(5) || ''`이다. 차트 축이 일부 눈금만 표시할 때 배포본의 날짜 라벨이 실제 위치와 어긋날 수 있다. 로그인된 앱의 저장 대화/데이터 화면은 동작하지만 **배포본과 저장소의 최신 코드가 일치한다고 볼 수 없다**.
- 10/27 최신 정적 파일 4개를 Vercel 업로드 API에 전송했으나 기존 프로젝트의 Production 배포 생성은 연결 계정 권한 오류 403으로 거부되었다. 사용자 선택에 따라 CLI 인증은 건너뛰었다. 남은 실제 조치는 Vercel 프로젝트 Overview에 `.deploy/vercel` 폴더를 수동 드롭해 Production을 갱신하고, 배포 Source의 위 콜백과 로그인된 앱을 다시 확인하는 것이다. 파일 업로드만으로 배포가 완료된 것으로 세지 않는다.
- GitHub 저장소는 사용자의 선택에 따라 Public, Vercel 실행 화면은 로그인 보호 유지. PR #1은 검토용 초안, `main` 병합 전이다. 시연자는 Vercel 팀에 로그인해야 하며 제3자는 README의 프론트 URL만으로 화면을 볼 수 없다.

인수 항목별 URL·화면·테스트는 [검사표](acceptance.md)에서 확인한다.
