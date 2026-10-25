# backend/database.py
import base64
import binascii
import json
import logging
import os
import threading

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger("database")

_lock = threading.Lock()
_db = None


def _load_service_account() -> dict:
    """FIREBASE_SERVICE_ACCOUNT_JSON (JSON 문자열 또는 Base64) 을 dict 로 파싱."""
    raw = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise RuntimeError(
            "환경변수 FIREBASE_SERVICE_ACCOUNT_JSON 이 설정되지 않았습니다."
        )

    # 앞뒤 따옴표 제거 (환경변수 UI에서 따옴표가 함께 들어가는 경우 대비)
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        raw = raw[1:-1].strip()

    try:
        if raw.startswith("{"):
            info = json.loads(raw)
        else:
            decoded = base64.b64decode(raw).decode("utf-8")
            info = json.loads(decoded)
    except (json.JSONDecodeError, binascii.Error, UnicodeDecodeError) as exc:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON 파싱 실패: 올바른 JSON 문자열 또는 "
            "Base64 인코딩 값인지 확인하세요."
        ) from exc

    # 환경변수 과정에서 개행이 '\\n' 문자열로 들어온 경우 복원
    pk = info.get("private_key")
    if isinstance(pk, str) and "\\n" in pk:
        info["private_key"] = pk.replace("\\n", "\n")

    return info


def init_firebase():
    """Firebase Admin SDK 를 (한 번만) 초기화하고 Firestore 클라이언트를 반환."""
    global _db
    if _db is not None:
        return _db

    with _lock:
        if _db is not None:
            return _db

        info = _load_service_account()
        try:
            if not firebase_admin._apps:  # noqa: SLF001
                cred = credentials.Certificate(info)
                firebase_admin.initialize_app(cred)
            _db = firestore.client()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Firebase 초기화 실패: {exc}") from exc

        logger.info("Firestore client ready (project=%s)", info.get("project_id"))
        return _db


def get_db():
    """Firestore 클라이언트 반환 (필요 시 지연 초기화)."""
    return init_firebase()