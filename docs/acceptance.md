# AI 비서 인수 검사표

최종 대조일: 2026-10-27 (Asia/Seoul). 10/25 Function Calling·화면 증거와 10/27 새 회귀·Render/MCP·GPT 검사를 구분한다. 사용자가 지정한 원본 폴더를 기준 작업 폴더로 정리하고 이 저장소의 `codex/ai-assistant-completion` 브랜치에서 검증했다. [원본 미션·승인 계획 대조](mission-audit-2026-10-27.md).

| 대상 | 결과 | 근거 |
|---|---|---|
| A1 Python·가상환경·패키지 재현 | 통과 | [README 실행법](../README.md), 고정 의존성 [`requirements.lock.txt`](../backend/requirements.lock.txt), Render Python 3.13.14 배포 |
| A2 날짜·값·메모 100건 이상 | 통과 | Firestore `data` 122건(2026-06-01~09-30), [출처·이용조건](../datasets/README.md), [CSV](../datasets/seoul-temperature.csv), [공개 데이터 화면](screenshots/vercel-data-live.png) |
| A3 데이터 CRUD·요약·검증 | 통과 | [실제 Render API 15항목 검사](test-results/api-live.json). 추가→조회→수정→삭제, 422/404와 요약 재대조, 임시 기록 제거 |
| A4 수동 대화 CRUD·복원 | 통과 | [실제 Render API 검사](test-results/api-live.json), [수동 저장·복원 화면](screenshots/history-manual-local.png) |
| A5 최신 데이터에 근거한 GPT 답변·자동 저장 | 통과 | [실키 응답·도구 호출·재조회 기록](test-results/live-chat-current.json). 전체 122건, 평균 25.1℃, 6월 23.7℃와 9월 21.9℃ 비교. 10/27 [새 GPT 호출·자동 저장·삭제](test-results/desktop-migration-chat.json)도 성공. [Vercel에서 저장 대화 복원](screenshots/vercel-ai-history-live.png) |
| A6 채팅·로딩·CRUD·요약·대화 목록 UI | 통과, 배포 동기화 필요 | [로딩 화면](screenshots/chat-loading.png), [CRUD 화면](screenshots/crud-local.png), [수동 대화 화면](screenshots/history-manual-local.png), [배포 데이터 화면](screenshots/vercel-data-live.png). Vercel 배포 그래프의 x축 날짜 콜백은 저장소 최신본보다 이전 버전 |
| A7 Render·Vercel HTTPS·API 연결·CORS | **조건부** | [Render API](https://m1-2-codyssey.onrender.com), [Swagger](https://m1-2-codyssey.onrender.com/docs) 정상, 배포 origin CORS preflight 200. [Vercel 프론트](https://m1-2-codyssey-frontend.vercel.app)는 Ready이고 로그인된 팀 브라우저에서 데이터 122건·저장 대화를 조회했으나, 비로그인 HTTP는 Vercel Login을 반환한다. 사용자가 심사 시 자신의 로그인 세션으로 시연하기로 선택 |
| A8 README·링크·설치법·화면 3종 | 통과 | [README](../README.md)의 채팅·데이터 수정·대화 복원 화면 3종을 본문에 포함, 환경변수·배포 절차·접근 제한 명시 |
| A9 키·입력·오류·시간 제한 | 통과 | 환경변수만 사용, `frontend/config.js`에는 공개 URL만 저장. 날짜·유한수·기간·공백 검증, GPT 시간/라운드/속도 상한, Firestore [직접 클라이언트 접근 차단](screenshots/firestore-rules.png). 코드 및 회귀 검사로 확인 |
| B1 GPT Function Calling | 통과 | [실제 질문 결과](test-results/live-chat-current.json)의 `tool_calls_used=["get_data_summary"]`, 기간별 세 번의 요약 조회와 API 수치 일치. [화면](screenshots/vercel-ai-history-live.png)의 도구 사용 표시 |
| B2 독립 MCP 클라이언트 | 통과 | 별도 stdio 프로세스에서 handshake→list_tools→call_tool, Render API와 요약값 일치: [증거](test-results/mcp-live.json). [실행법](../README.md#mcp-외부-클라이언트) |
| B3 추가 지표·그래프·CSV·다크 모드 | 기능 통과, 그래프 라벨 재배포 필요 | 합계·최근 7건 추세 [배포 화면](screenshots/vercel-data-live.png), 122행 UTF-8 BOM CSV [API 검사](test-results/api-live.json), [다크 모드](screenshots/dark-mode.png). 축 라벨 콜백 수정은 저장소에 있으나 [배포본 Source](screenshots/vercel-source-drift.jpg)에 미반영 |
| A10 제출 전 근거 연결 | 통과 | 본 검사표와 [미션 대조표](mission-audit-2026-10-27.md)에 통과/조건부를 구분. Render 무료 서비스는 유휴 후 기동 지연이 있다 |

검사 범위: 10/27 Python 회귀 검사 64개, Node UI/설정 검사 8개, 의존성 검사, 실제 Render API CRUD/요약·CSV 15항목, 독립 MCP 클라이언트의 Render API 값 일치. 10/25 Function Calling과 Vercel 로그인 브라우저의 데이터/대화 복원 증거를 보존했다. 10/27 Desktop 로컬 API는 Firestore 122건·평균 25.1197℃를 조회하고 새 GPT 질문에 HTTP 200으로 답했으며, 대화 2개 메시지 저장·재조회 뒤 임시 대화를 204로 삭제했다. 이전 GPT 질문 4개는 인증·선불 잔액 문제 때 실패했으므로 성공으로 세지 않았다.

Vercel은 CLI 없이 **대시보드 Drop to Deploy**로 프론트 정적 파일 4개를 업로드했다. 현재 GitHub 자동 배포 연결은 없으며 프론트 변경을 배포본에 반영하려면 수동 재배포가 필요하다. 10/27 배포 Source의 `app.js` 584행은 이전 그래프 날짜 라벨 콜백이고 저장소 최신본과 다르다. 최신 4개 파일은 `.deploy/vercel/`에 준비했으나 Vercel 연결 도구의 Production 배포 생성 권한이 403으로 거부되어 **재배포 완료로 판단하지 않는다**. 프로젝트 Overview에서 폴더를 다시 드롭한 후 배포 Source와 앱을 재확인해야 한다. GitHub 저장소는 사용자의 선택에 따라 Public이고 초안 PR은 [jec5500-prog/M1-2-codyssey](https://github.com/jec5500-prog/M1-2-codyssey/pull/1)에 있다. Vercel의 `Require Log In: All Deployments`는 사용자의 선택에 따라 유지한다. Render는 이 브랜치의 `cbe6da7`을 배포했다. `main` 병합은 하지 않았다.
