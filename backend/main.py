# backend/main.py
import logging
import os
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.api_core.exceptions import GoogleAPICallError

load_dotenv(Path(__file__).with_name('.env'), override=False)


from database import init_firebase  # noqa: E402
from routers import chat, data  # noqa: E402
from settings import load_settings  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 Firebase 초기화 시도 (실패해도 서버는 기동, 요청 시 재시도)
    try:
        init_firebase()
        logger.info("Firebase initialized")
    except Exception as exc:  # noqa: BLE001
        logger.error("Firebase init failed at startup: %s", type(exc).__name__)
    yield


app = FastAPI(
    title="Data Chatbot API",
    description="시계열 데이터 기반 AI 챗봇 백엔드 (FastAPI + Firestore + OpenAI)",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------- CORS
settings = load_settings()
origins = settings.allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


# ---------------------------------------------------------------- 예외 처리
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # Raw JSON may contain infinity/NaN; do not echo non-JSON values or inputs.
    errors=[{key:error[key] for key in ('loc','msg','type')} for error in exc.errors()]
    return JSONResponse(status_code=422,content={'detail':errors})


@app.exception_handler(GoogleAPICallError)
async def firestore_error_handler(request: Request, exc: GoogleAPICallError):
    request_id=uuid.uuid4().hex[:12]
    logger.error("Firestore error id=%s type=%s", request_id, type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "데이터베이스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.", "request_id":request_id},
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    request_id=uuid.uuid4().hex[:12]
    logger.error("Configuration error id=%s type=%s", request_id, type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "서버 연결 설정을 확인해 주세요.", "request_id":request_id})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    request_id=uuid.uuid4().hex[:12]
    logger.error("Unhandled error id=%s type=%s", request_id, type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다.", "request_id":request_id},
    )


# ---------------------------------------------------------------- 라우터
app.include_router(data.router)
app.include_router(chat.router)


@app.get("/", tags=["health"])
def root():
    return {"service": "data-chatbot-api", "status": "ok", "docs": "/docs"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
