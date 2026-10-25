# backend/models.py
import re
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, FiniteFloat, field_validator

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_date_str(v: str) -> str:
    if not isinstance(v, str) or not _DATE_RE.match(v):
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다.")
    try:
        datetime.strptime(v, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("존재하지 않는 날짜입니다.") from exc
    return v


# ------------------------------------------------------------------ 데이터 도메인
class DataPointBase(BaseModel):
    date: str = Field(..., description="날짜 (YYYY-MM-DD)", examples=["2025-01-31"])
    value: FiniteFloat = Field(..., description="유한한 측정값")
    memo: str = Field("", max_length=500, description="메모")

    @field_validator("date")
    @classmethod
    def _check_date(cls, v: str) -> str:
        return validate_date_str(v)


class DataPointCreate(DataPointBase):
    pass


class DataPointUpdate(BaseModel):
    date: Optional[str] = None
    value: Optional[FiniteFloat] = None
    memo: Optional[str] = Field(None, max_length=500)

    @field_validator("date")
    @classmethod
    def _check_date(cls, v: Optional[str]) -> Optional[str]:
        return validate_date_str(v) if v is not None else v


class DataPoint(DataPointBase):
    id: str


class PointRef(BaseModel):
    date: str
    value: float
    memo: str = ""


class TrendInfo(BaseModel):
    direction: Literal["up", "down", "flat", "insufficient"]
    label: str
    window: int = Field(0, description="추세 계산에 사용된 최근 데이터 개수")
    slope: Optional[float] = Field(None, description="회귀선 기울기(데이터 1건당 변화량)")
    change_percent: Optional[float] = Field(
        None, description="윈도우 첫 값 대비 마지막 값 변화율(%)"
    )
    recent_average: Optional[float] = None


class Summary(BaseModel):
    count: int
    average: Optional[float] = None
    total: Optional[float] = None
    minimum: Optional[PointRef] = None
    maximum: Optional[PointRef] = None
    latest: Optional[PointRef] = None
    first_date: Optional[str] = None
    last_date: Optional[str] = None
    trend: TrendInfo


# ------------------------------------------------------------------ 챗 도메인
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("메시지가 비어 있습니다.")
        return v


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    tool_calls_used: List[str] = []


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str
    tools_used: List[str] = []


class ConversationMeta(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class ConversationDetail(ConversationMeta):
    messages: List[ChatMessage] = []


class MessageInput(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator('content')
    @classmethod
    def nonblank(cls, value: str) -> str:
        value=value.strip()
        if not value: raise ValueError('메시지가 비어 있습니다.')
        return value


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    messages: List[MessageInput] = Field(..., min_length=1, max_length=200)
