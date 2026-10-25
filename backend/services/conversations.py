"""One persistence policy for manual transcripts and automatic chat turns."""
import json
import re
from datetime import datetime, timezone
from time import monotonic as clock

from fastapi import HTTPException
from google.cloud import firestore
from google.api_core.exceptions import FailedPrecondition, Aborted

from database import get_db
from models import ConversationCreate

MAX_MESSAGES = 200
MAX_BYTES = 900_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _collection():
    return get_db().collection('conversations')


def _ref(id: str):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',id):
        raise HTTPException(404,'대화를 찾을 수 없습니다.')
    return _collection().document(id)


def _check_capacity(messages: list[dict]):
    if len(messages)>MAX_MESSAGES or len(json.dumps(messages,ensure_ascii=False).encode('utf8'))>MAX_BYTES:
        raise HTTPException(409,'대화 저장 한도에 도달했습니다. 기존 기록은 보존됩니다. 새 대화를 시작해 주세요.')


def _meta(id: str, data: dict) -> dict:
    return {'id':id,'title':data.get('title','새 대화'),'created_at':data.get('created_at',''),
            'updated_at':data.get('updated_at',''),'message_count':len(data.get('messages',[]))}


def get_conversation(id: str, *, timeout: float=10) -> dict:
    snap=_ref(id).get(timeout=timeout,retry=None)
    if not snap.exists: raise HTTPException(404,'대화를 찾을 수 없습니다.')
    data=snap.to_dict()
    return {**_meta(id,data),'messages':data.get('messages',[])}


def list_conversations(limit: int=50) -> list[dict]:
    docs=_collection().order_by('updated_at',direction=firestore.Query.DESCENDING).limit(limit).stream(timeout=10,retry=None)
    return [_meta(doc.id,doc.to_dict()) for doc in docs]


def save_conversation(title: str | None, messages: list[dict]) -> dict:
    payload=ConversationCreate(title=title,messages=messages)
    now=_now()
    stored=[{**m.model_dump(),'timestamp':now,'tools_used':[]} for m in payload.messages]
    _check_capacity(stored)
    ref=_collection().document()
    body={'title':(payload.title or payload.messages[0].content[:40]).strip() or '새 대화',
          'created_at':now,'updated_at':now,'messages':stored}
    ref.create(body,timeout=10,retry=None)
    return {**_meta(ref.id,body),'messages':stored}


def _rpc_timeout(deadline: float | None) -> float:
    seconds=10 if deadline is None else deadline-clock()
    if seconds<=0:
        raise HTTPException(504,'대화 저장 시간이 초과되었습니다. 기록을 확인한 뒤 다시 시도해 주세요.')
    return min(10,seconds)


def append_turn(conversation_id: str | None,user: str,assistant: str,tools_used: list[str], *, deadline: float | None=None) -> str:
    db=get_db()
    ref=_ref(conversation_id) if conversation_id else db.collection('conversations').document()

    # Public version preconditions make each append atomic without unbounded
    # transaction begin/commit retries. Every RPC shares the request deadline.
    for attempt in range(3):
        snap=ref.get(timeout=_rpc_timeout(deadline),retry=None)
        if conversation_id and not snap.exists: raise HTTPException(404,'대화가 삭제되었습니다. 새 대화를 시작해 주세요.')
        body=snap.to_dict() if snap.exists else {'title':' '.join(user.split())[:40], 'created_at':_now(),'messages':[]}
        stored=list(body.get('messages',[]))
        stored.extend([
            {'role':'user','content':user,'timestamp':_now(),'tools_used':[]},
            {'role':'assistant','content':assistant,'timestamp':_now(),'tools_used':list(tools_used)},
        ])
        _check_capacity(stored)
        body={**body,'messages':stored,'updated_at':_now()}
        try:
            if conversation_id:
                option=db.write_option(last_update_time=snap.update_time)
                ref.update(body,option=option,timeout=_rpc_timeout(deadline),retry=None)
            else:
                ref.create(body,timeout=_rpc_timeout(deadline),retry=None)
            _rpc_timeout(deadline)
            return ref.id
        except (FailedPrecondition,Aborted):
            _rpc_timeout(deadline)
    raise HTTPException(409,'동시에 대화가 변경되었습니다. 기록을 다시 불러온 뒤 시도해 주세요.')


def check_room_for_turn(messages: list[dict]):
    # Reserve room before a paid call; actual UTF-8 bytes are checked again on save.
    prospective=messages+[
        {'role':'user','content':'한'*4000,'timestamp':_now(),'tools_used':[]},
        {'role':'assistant','content':'한'*4000,'timestamp':_now(),'tools_used':[]},
    ]
    _check_capacity(prospective)


def delete_conversation(id: str):
    ref=_ref(id)
    if not ref.get(timeout=10,retry=None).exists: raise HTTPException(404,'대화를 찾을 수 없습니다.')
    ref.delete(timeout=10,retry=None)
