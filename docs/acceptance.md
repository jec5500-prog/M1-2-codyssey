# AI 비서 인수 검사표

검증일: 2026-10-25 (Asia/Seoul). 원본 폴더는 유지하고 이 저장소의 `codex/ai-assistant-completion` 브랜치에서 검증했다.

| 대상 | 결과 | 근거 |
|---|---|---|
| A1 Python·가상환경·패키지 재현 | 통과 | [README 실행법](../README.md), 고정 의존성 [`requirements.lock.txt`](../backend/requirements.lock.txt), Render Python 3.13.14 배포 |
| A2 날짜·값·메모 100건 이상 | 통과 | Firestore `data` 122건(2026-06-01~09-30), [출처·이용조건](../datasets/README.md), [CSV](../datasets/seoul-temperature.csv), [공개 데이터 화면](screenshots/vercel-data-live.png) |
| A3 데이터 CRUD·요약·검증 | 통과 | [실제 Render API 15항목 검사](test-results/api-live.json). 추가→조회→수정→삭제, 422/404와 요약 재대조, 임시 기록 제거 |
| A4 수동 대화 CRUD·복원 | 통과 | [실제 Render API 검사](test-results/api-live.json), [수동 저장·복원 화면](screenshots/history-manual-local.png) |
| A5 최신 데이터에 근거한 GPT 답변·자동 저장 | 통과 | [실키 응답·도구 호출·재조회 기록](test-results/live-chat-current.json). 전체 122건, 평균 25.1℃, 6월 23.7℃와 9월 21.9℃ 비교. [Vercel에서 저장 대화 복원](screenshots/vercel-ai-history-live.png) |
| A6 채팅·로딩·CRUD·요약·대화 목록 UI | 통과 | [로딩 화면](screenshots/chat-loading.png), [CRUD 화면](screenshots/crud-local.png), [수동 대화 화면](screenshots/history-manual-local.png), [공개 데이터 화면](screenshots/vercel-data-live.png) |
| A7 Render·Vercel HTTPS·API 연결·CORS | 통과 | [Render API](https://m1-2-codyssey.onrender.com), [Swagger](https://m1-2-codyssey.onrender.com/docs), [Vercel 프론트](https://m1-2-codyssey-frontend.vercel.app), [Render 배포](screenshots/render-live.png), [Vercel Ready](screenshots/vercel-ready.png). 공개 브라우저에서 122건 데이터와 저장 대화 실제 조회 |
| A8 README·링크·설치법·화면 3종 | 통과 | [README](../README.md), 이 표의 채팅·데이터/CRUD·대화 복원 화면 |
| A9 키·입력·오류·시간 제한 | 통과 | 환경변수만 사용, `frontend/config.js`에는 공개 URL만 저장. 날짜·유한수·기간·공백 검증, GPT 시간/라운드/속도 상한, Firestore [직접 클라이언트 접근 차단](screenshots/firestore-rules.png). 코드 및 회귀 검사로 확인 |
| B1 GPT Function Calling | 통과 | [실제 질문 결과](test-results/live-chat-current.json)의 `tool_calls_used=["get_data_summary"]`, 기간별 세 번의 요약 조회와 API 수치 일치. [화면](screenshots/vercel-ai-history-live.png)의 도구 사용 표시 |
| B2 독립 MCP 클라이언트 | 통과 | 별도 stdio 프로세스에서 handshake→list_tools→call_tool, Render API와 요약값 일치: [증거](test-results/mcp-live.json). [실행법](../README.md#mcp-외부-클라이언트) |
| B3 추가 지표·그래프·CSV·다크 모드 | 통과 | 합계·최근 7건 추세 [공개 화면](screenshots/vercel-data-live.png), 122행 UTF-8 BOM CSV [API 검사](test-results/api-live.json), [다크 모드](screenshots/dark-mode.png) |
| A10 제출 전 근거 연결 | 통과 | 본 검사표, 위 URL·실서비스 JSON·화면. Render 무료 서비스는 유휴 후 기동 지연이 있다 |

검사 범위: Python 회귀 검사 64개, Node UI/설정 검사 8개, 실제 Render API CRUD/요약·CSV, 실제 Firestore 원자 저장, 실제 GPT 질문 1개 성공, 독립 MCP 클라이언트, 공개 Vercel 브라우저 데이터/대화 조회. GPT 질문 4개는 인증·선불 잔액 문제 때 실패했으며 이를 성공으로 세지 않았다. 이후 잔액 보충 후 실키 질문이 성공했다.

Vercel은 CLI 없이 **대시보드 Drop to Deploy**로 프론트 정적 파일 4개를 업로드했다. 현재 GitHub 자동 배포 연결은 없으며 프론트 변경을 공개 URL에 반영하려면 수동 재배포가 필요하다. GitHub 저장소와 초안 PR은 [jec5500-prog/M1-2-codyssey](https://github.com/jec5500-prog/M1-2-codyssey/pull/1)에 있다. Render는 이 브랜치의 `cbe6da7`을 배포했다. `main` 병합은 하지 않았다.
