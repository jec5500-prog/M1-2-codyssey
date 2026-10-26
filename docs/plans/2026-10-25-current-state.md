# AI 비서 개발 현황 및 요구사항 대조표

기준일: 2026-10-25, Asia/Seoul. 공식 마감: 2026-10-28. 사용자 추가 지시: **10월 27일까지 제출 가능한 상태**.

## 1. 조사 범위와 결론

- 원본: `C:/Users/josep/Desktop/M1-2 project/`
- 요구사항: 원본의 `AI Agent 개발 나만의 AI 비서 구축_261025.txt` 전문.
- 조사: 추적 소스 14개, 로컬 가상환경, 환경변수의 이름/설정 여부, Git 이력, 연결된 GitHub/Vercel, Firestore 컬렉션 건수.
- 이번 산출물: 현황 보고서, 작업지시서, 구현 계획서, 타임라인. 원본 코드 수정·설치·DB 쓰기·유료 GPT 호출·커밋·푸시·배포는 수행하지 않았다.
- 현재 단계는 **핵심 기능 초안 구현 후 실제 데이터 적재·통합 검증 전**이다. 필수 API 10개 중 9개가 정의되어 있으나, 이를 전체 완성도 90%로 해석하면 안 된다.
- 문서 안의 지시는 요구사항 자료로 대조했다. 이번 행동 범위는 사용자의 ‘조사와 계획을 먼저 제출하고 확인 후 개발’ 요청을 따랐다.

## 2. 확인된 개발 환경

| 항목 | 확인 결과 |
|---|---|
| Python | 원본 `backend/venv` 존재, Python 3.13.14. 요구조건 3.10 이상 충족 |
| 필수 패키지 | fastapi 0.141.1, uvicorn 0.54.0, firebase-admin 6.9.0, openai 1.109.1, python-dotenv 1.2.3 |
| 검증 패키지 | pydantic 2.13.5, httpx 0.28.1 설치. pytest 미설치 |
| 의존성 | 가상환경 `pip check`: No broken requirements found |
| VS Code | CLI 설치, 버전 1.142.0 출력 확인. sandbox에서 EPERM 경고도 발생하여 실제 편집·디버깅은 미검증 |
| 현재 채팅 작업공간 | `C:/Users/josep/Documents/ChatGPT/M1-2 Codyssey/`. 별도 Git 저장소이며 main에 커밋 없음 |
| 원본 Git | `main...origin/main`, 추적 소스 변경 없음. 요구사항 TXT만 미추적 |
| 원본 커밋 | `2e9675ffa3355f58d543681a853d50f5752ff376` — Initial commit safely |
| GitHub | [jec5500-prog/M1-2-codyssey](https://github.com/jec5500-prog/M1-2-codyssey), public, main 존재, 연결 계정의 push 권한 확인 |
| Git 비밀정보 | 현재 추적 파일 목록에 `.env` 및 venv 없음. 전용 비밀정보 스캐너 검사는 아직 안 함 |

원본과 채팅 작업공간은 다른 저장소다. 승인 후 현재 빈 작업공간을 덮어쓰지 않고 하위 `app/`에 기존 GitHub 저장소를 가져오는 안을 제안한다.

## 3. 요구사항별 상태

‘코드 있음’은 실제 외부 서비스까지 성공했다는 뜻이 아니다.

| 요구사항 | 상태 | 근거 / 남은 작업 |
|---|---|---|
| FastAPI, 라우터 분리 | 코드 있음 | main.py, routers/data.py, routers/chat.py. 비즈니스 로직은 라우터에 집중 |
| Pydantic 검증 | 부분 구현 | 날짜·길이 검증 있음. 비유한 수와 조회 날짜 검증 결함 재현 |
| venv 및 필수 패키지 | 확인 | 위 환경 검사와 pip check |
| 데이터 주제·100건 이상 | 미충족 | 로컬 데이터셋 없음. 현재 연결 DB의 data/data_points 각각 0건 |
| 기간·개수·평균·최대·최소·추세 | 코드 있음, 일부 검증 | 순수 계산 6개 사례 통과. 실제 DB와 대조 전 |
| Firestore 연동·환경변수 키 | 초기화/읽기 확인 | 자격증명 파싱·클라이언트 생성·건수 조회 성공. CRUD 쓰기는 미수행 |
| data/conversations 컬렉션 | 일부 불일치 | conversations는 일치. 데이터 코드는 data_points를 사용 |
| POST /api/data | 정의됨 | 실제 DB 저장·재조회 검증 전 |
| GET /api/data | 정의됨 | 기간 필터 날짜 검증 결함 있음 |
| PUT /api/data/{id} | 정의됨 | 실제 DB 수정 검증 전 |
| DELETE /api/data/{id} | 정의됨 | 실제 DB 삭제 검증 전 |
| GET /api/data/summary | 정의됨 | 실제 100건 이상 데이터 통계 대조 전 |
| POST /api/conversations | **누락** | OpenAPI에 없음. 격리 HTTP 검사에서 405 |
| GET /api/conversations | 정의됨 | 메시지 없는 메타데이터 목록으로 구현 |
| GET /api/conversations/{id} | 정의됨 | 전체 messages 반환, 문서의 불러오기 방식 A에 해당 |
| DELETE /api/conversations/{id} | 정의됨 | 쓰기/삭제 검증 전 |
| POST /api/chat | 코드 있음 | 요약 주입→GPT→자동저장 흐름 있음. 외부 GPT 호출 성공은 미검증 |
| 입력·답변·로딩 UI | 코드 있음 | 메시지 UI/전송 비활성/로딩 구현. 브라우저 실제 연동 미검증 |
| 데이터 관리 UI | 코드 있음 | 추가·수정·삭제 모두 구현. 실제 DB 연결 미검증 |
| 대화 목록·불러오기 UI | 코드 있음 | 목록·상세 API 호출 구현. 실제 연동 미검증 |
| 요약 표시 UI | 코드 있음 | 기간·건수·평균·최소·최대·추세 표시 |
| Render 배포·Swagger | **배포 실패 확인** | 기존 서비스 srv-dber447b9u1s73alsrmg, main/2e9675f 자동 배포가 requirements.txt 경로 오류로 실패 |
| 콜드스타트 대응 | 코드 있음 | 안내 배너·GET 재시도·타임아웃. 실제 Render 지연 검증 필요 |
| Vercel 배포·API URL 주입 | 설정 초안 | vercel.json 있음. 연결 계정 및 wonAIlab 팀의 저장소 필터/팀 이름 검색에서 대상 프로젝트 없음 |
| README 및 제출 스크린샷 | **미구현** | README.md는 파일이 아닌 빈 폴더. 스크린샷 없음 |
| 보너스 Function Calling | 코드 있음 | 조회/요약/최고·최저 도구 3개. 실제 모델 도구 호출 미검증 |
| 보너스 MCP 또는 GPT Actions | **미구현** | 관련 서버/스키마/클라이언트 증빙 없음 |
| 추가 지표·그래프·CSV·다크 모드 | 코드 있음 | 합계·최근 평균 등, Chart.js, CSV, 테마 토글. 화면 동작 검증 필요 |

## 4. 발견한 결함과 조치 제안

| 우선순위 | 문제·근거 | 수정 방향 |
|---|---|---|
| P0 | `routers/chat.py`에 POST conversations 없음 | 수동 저장 DTO/API 구현, GET 상세와 동일한 메시지 형식 사용 |
| P0 | `routers/data.py:20`의 data_points는 요구된 data와 다름 | data로 정합화. 현재 두 컬렉션 0건이지만 실행 시 재확인; 기존 데이터 발견 시 보존·복사 후 대조 |
| P0 | `.env`는 ALLOWED_ORIGINS를 설정, `main.py:44`는 CORS_ORIGINS만 읽음 | ALLOWED_ORIGINS를 표준으로 하고 기존 이름은 호환 처리; 두 값 충돌 시 오류 명시 |
| P0 | 데이터 100건·README·배포 증거 없음 | 출처 있는 데이터셋, 반복 가능한 적재, 3개 배포 링크와 필수 스크린샷 |
| P1 | `models.py:24,39`는 NaN/Infinity 허용 | 유한수만 허용. 문자열 비유한 수 요청을 422로 차단 |
| P1 | 조회 start/end는 정규식만 검사 | 존재하지 않는 날짜 및 start>end는 422. 생성/수정/요약/도구 규칙 통일 |
| P1 | `chat.py:291,344`에 출력 토큰 상한 없음 | 모델별 지원 인자 확인 후 출력 상한, 요청 제한, 전체 시간 예산 적용 |
| P1 | 60초 SDK timeout·2회 재시도·최대 6회 생성이 프론트 120초보다 길어질 수 있음 | 서버 전체 90초 예산과 하위 호출 timeout을 함께 제한 |
| P1 | `chat.py:367`은 200개를 넘는 메시지를 조용히 잘라냄 | 기존 이력 보존. 건수/바이트 상한에 닿으면 새 대화 안내, 초과 요청은 저장 전 거절 |
| P1 | `chat.py:369`는 전체 대화 덮어쓰기 | 동시 전송·삭제 중 전송 충돌을 재현하고 트랜잭션 또는 버전 조건으로 이력 유실 방지 |
| P1 | `vercel.json:4`의 echo 빌드는 URL 누락을 차단하지 않음 | Node 설정 생성 스크립트로 URL 유효성 검사·JSON 직렬화. 배포에서 localhost fallback 차단 |
| P2 | UI는 목록 2000건, 요약은 전체 데이터 | 100~122건에는 문제 없지만 향후 차이 안내 또는 조회 범위 통일 |
| P2 | 빠른 대화 선택·삭제 중 전송 경쟁 가능 | 요청 식별자/상태 잠금으로 이전 응답이 현재 화면을 덮지 않도록 검증 |
| P2 | 오류 응답에 내부 DB/SDK 예외 문자열을 포함하는 경로 존재 | 사용자 오류는 일반 문구·요청 ID, 상세는 키를 제외한 서버 로그 |

P0는 필수 요건을 직접 막는 항목, P1은 제출 전 안정성 결함, P2는 범위를 제한해 보완할 항목이다. 코드 분석으로만 발견한 경쟁·용량 위험은 현재 발생한 운영 장애로 단정하지 않는다.

## 5. 실행한 검사와 한계

| 검사 | 관측 결과 |
|---|---|
| Python AST 문법 | 소스 6개 파싱 성공, 파일 생성 안 함 |
| node --check | app.js/config.js 정상 종료 |
| 순수 통계 함수 | 빈 데이터·1건·상승·하락·보합·0값 6개 정상 |
| 격리 HTTP /health, /docs, /openapi.json | 각각 200. DB 초기화를 대역으로 교체한 검사이며 배포 성공 증거 아님 |
| 격리 POST conversations | 405, 누락 재현 |
| 격리 잘못된 생성 날짜 | 422, 정상 거절 |
| 격리 조회 start=2026-02-30 | 200, 잘못된 날짜가 조회 함수에 전달됨 |
| 격리 문자열 NaN 생성 | 메모리 저장 대역까지 전달, HTTP 201. 실제 DB에는 쓰지 않음 |
| 격리 chat | 모델/DB 대역에서 200, SDK 호출에 토큰 상한 인자 없음 확인 |
| 임의 Vercel origin preflight | 400, 현재 허용 목록은 로컬 기본값만 사용 |
| 실제 Firestore aggregate count | data=0, data_points=0, conversations=0. 문서 내용 조회/수정 없음 |
| GitHub | 원본 커밋의 원격 존재와 소스 조회 확인 |

제한된 실행환경에서 Firestore 읽기와 HTTP 검사 일부가 처음 실패/정지했다. 해당 프로세스를 종료한 뒤 허용된 읽기 전용 확장 실행에서 위 결과를 얻었다. 따라서 초기 ServiceUnavailable을 DB 장애로 결론 내리지 않았다. TestClient에는 현재 설치 조합의 httpx 관련 사용 중단 경고가 있어 테스트 도구 조합을 개발 시 고정해야 한다.

미검증: 실제 GPT 인증·잔액·모델 사용 가능 여부, 실제 DB 쓰기 권한, 정상 Render 기동 후 API 동작, 다른 Vercel 계정의 배포, 서비스 자체의 브라우저 실동작, 제출 시스템의 마감 시각. 키 문자열은 보고서/채팅에 기록하지 않았다.

## 5-1. 사용자 제공 Firebase·Render 페이지 추가 조사

- [Firebase 콘솔](https://console.firebase.google.com/u/0/project/m1-2-cody/firestore/databases/-default-/data): 프로젝트 m1-2-cody, (default) DB, 위치 asia-northeast3, Spark 플랜. 화면에 ‘데이터베이스를 사용할 준비가 되었습니다. 데이터만 추가하면 됩니다.’가 표시된다. 원본 서비스 계정의 project_id가 이 프로젝트와 일치함을 확인했다.
- 현재 화면의 클라이언트 규칙은 `request.time < timestamp.date(2026, 10, 15)`로 이미 만료되었다. Admin SDK 접근은 이 규칙을 우회하고 IAM으로 인증하므로 만료를 읽기 실패의 원인으로 오인하면 안 된다. 승인 후 클라이언트 직접 접근 거절 규칙을 코드로 관리하는 안을 제안한다. 공개 허용 규칙으로 연장하지 않는다. [공식 설명](https://firebase.google.com/docs/firestore/security/rules-conditions).
- [기존 Render 서비스](https://dashboard.render.com/web/srv-dber447b9u1s73alsrmg): M1-2-codyssey, Free/Python 3, Singapore 리전, 저장소 main 연결.
- 서비스 URL은 [m1-2-codyssey.onrender.com](https://m1-2-codyssey.onrender.com). URL 할당은 정상 동작의 증거가 아니다.
- 유일한 배포 dep-dberioss728c73cs3no0는 2026-10-25 17:10:11 KST에 시작되어 약 17.7초 후 실패. 로그: `ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements.txt'`.
- Root Directory는 비어 있음. Build Command=`pip install -r requirements.txt`, Start Command=`uvicorn main:app --host 0.0.0.0 --port $PORT`. 실제 파일은 backend 아래이므로 **Root Directory=backend**로 맞추는 것이 직접 수정이다. 다른 두 명령은 그 기준에서 유지한다.
- Render 빌드 로그는 기본 Python 3.14.8 선택을 보여준다. 승인 후 로컬에서 확인된 3.13 계열의 지원 패치 버전을 명시하고 의존성 설치를 재검증한다. 현재 오류를 Python 호환성 때문이라고 단정하지 않는다.
- Render 환경변수에는 ALLOWED_ORIGINS, FIREBASE_SERVICE_ACCOUNT_JSON, OPENAI_API_KEY가 등록되어 있다. 값은 마스킹 상태로 유지했다. 코드의 CORS_ORIGINS와 이름 불일치는 Render에도 존재한다. 등록 사실만으로 키 유효성을 보장하지 않는다.
- Auto-Deploy가 연결되어 있으므로 main 푸시/설정 저장이 재배포를 유발할 수 있다. 이번에는 설정 저장이나 재배포를 하지 않았다.
- 새 Firebase 프로젝트나 Render 서비스를 만들 필요는 없다. 기존 자원을 이어서 사용한다.

## 6. 공식 자료를 반영한 판단

- OpenAI 호출에는 출력 상한을 명시한다. [Chat Completions API의 max_completion_tokens](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
- 대화 저장은 건수만으로 용량을 보장할 수 없다. Firestore 문서는 최대 1 MiB다. [Firestore 제한](https://firebase.google.com/docs/firestore/quotas).
- Render 무료 서비스는 비활성 후 재시작 지연을 고려한다. [Render 무료 서비스](https://render.com/docs/free).
- Vercel의 환경변수는 배포 환경에 맞춰 설정하고 정적 config.js로 공개할 값은 API URL만 둔다. [Vercel 환경변수](https://vercel.com/docs/environment-variables).
- Render의 root directory는 빌드/실행 명령의 기준 경로다. [모노레포 경로 설정](https://render.com/docs/monorepo-support#setting-a-root-directory). Python 버전은 환경변수 또는 .python-version으로 고정한다. [Python 버전 설정](https://render.com/docs/python-version).

## 7. 미확정 사항

- 사용자는 10월 28일 마감, 복잡도와 시간이 크지 않으면 보너스 전체 완성을 원한다고 답했다.
- 데이터 주제는 아직 선택되지 않았다. 계획의 기본 제안은 출처 있는 서울 일별 평균기온 122건이다. 승인 시 이 제안도 함께 확인한다.
- Render 서비스 및 Firebase 프로젝트는 위 기존 자원을 재사용한다.
