from typing import List
from fastapi import APIRouter, Query, Request
from models import ChatRequest, ChatResponse, ConversationDetail, ConversationMeta, ConversationCreate
from services import conversations, ai_chat

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    ai_chat.limiter.check(request.client.host if request.client else "unknown")
    return ai_chat.run_chat(req.message, req.conversation_id)


@router.post("/conversations", response_model=ConversationDetail, status_code=201)
def save_conversation(payload: ConversationCreate):
    return conversations.save_conversation(payload.title, [m.model_dump() for m in payload.messages])


@router.get("/conversations", response_model=List[ConversationMeta])
def list_conversations(limit: int = Query(50, ge=1, le=200)):
    return conversations.list_conversations(limit)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str):
    return conversations.get_conversation(conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str):
    conversations.delete_conversation(conversation_id)
