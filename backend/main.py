# backend/main.py
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.api_core.exceptions import GoogleAPICallError

load_dotenv(override=True)


from database import init_firebase  # noqa: E402
from routers import chat, data  # noqa: E402

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
        logger.error("Firebase init failed at startup: %s", exc)
    yield


app = FastAPI(
    title="Data Chatbot API",
    description="시계열 데이터 기반 AI 챗봇 백엔드 (FastAPI + Firestore + OpenAI)",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------- CORS
_origins_raw = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8080",
)
origins = [o.strip().rstrip("/") for o in _origins_raw.split(",") if o.strip()]
allow_all = "*" in origins
origin_regex = os.getenv("CORS_ORIGIN_REGEX") or None  # 예: https://.*\.vercel\.app

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else origins,
    allow_origin_regex=None if allow_all else origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


# ---------------------------------------------------------------- 예외 처리
@app.exception_handler(GoogleAPICallError)
async def firestore_error_handler(request: Request, exc: GoogleAPICallError):
    logger.exception("Firestore error")
    return JSONResponse(
        status_code=503,
        content={"detail": f"데이터베이스 오류가 발생했습니다: {exc.message}"},
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    logger.exception("Runtime error")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다."},
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