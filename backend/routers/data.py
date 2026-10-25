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
from models import DataPoint, DataPointCreate, DataPointUpdate, Summary, validate_date_str
from services.data_summary import compute_summary

logger = logging.getLogger("data")

router = APIRouter(prefix="/api/data", tags=["data"])

COLLECTION = "data"
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


def validate_period(start=None, end=None):
    try:
        if start: validate_date_str(start)
        if end: validate_date_str(end)
        if start and end and start > end:
            raise ValueError("시작일은 종료일보다 늦을 수 없습니다.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def fetch_points(
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
    descending: bool = False,
) -> List[Dict[str, Any]]:
    """기간 필터/정렬/개수 제한을 적용해 데이터 포인트 목록을 반환 (챗 도구에서도 재사용)."""
    validate_period(start, end)
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
    return [_doc_to_point(d) for d in query.stream(timeout=10, retry=None)]






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
