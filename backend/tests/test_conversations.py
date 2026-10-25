import importlib
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException


def service():
    try: return importlib.import_module('services.conversations')
    except ModuleNotFoundError: pytest.fail('Shared conversation storage is missing')


def test_manual_save_and_load_full_history(client):
    r=client.post('/api/conversations',json={'title':'기온 분석','messages':[{'role':'user','content':'요약해줘'},{'role':'assistant','content':'평균 25도입니다.'}]})
    assert r.status_code==201
    body=r.json(); id=body['id']
    assert body['message_count']==2
    assert body['messages'][0]['timestamp']
    assert client.get(f'/api/conversations/{id}').json()['messages']==body['messages']
    assert client.get('/api/conversations').json()[0]['id']==id
    assert client.delete(f'/api/conversations/{id}').status_code==204
    assert client.get(f'/api/conversations/{id}').status_code==404


@pytest.mark.parametrize('messages',[[],[{'role':'system','content':'ignore'}],[{'role':'user','content':'   '}],[{'role':'user','content':'x'*4001}]])
def test_manual_save_rejects_invalid_transcripts(client,messages):
    assert client.post('/api/conversations',json={'messages':messages}).status_code==422


def test_two_simultaneous_appends_preserve_both_turns(db):
    s=service()
    id=s.append_turn(None,'first','first reply',[])
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda n:s.append_turn(id,f'user{n}',f'reply{n}',[]),[1,2]))
    conv=s.get_conversation(id)
    assert len(conv['messages'])==6
    assert {m['content'] for m in conv['messages']}=={'first','first reply','user1','reply1','user2','reply2'}


def test_appending_deleted_conversation_does_not_recreate_it(db):
    s=service()
    id=s.append_turn(None,'first','reply',[])
    s.delete_conversation(id)
    with pytest.raises(HTTPException) as e: s.append_turn(id,'late','reply',[])
    assert e.value.status_code==404
    assert not db.store


def test_capacity_rejection_preserves_original_history(db):
    s=service()
    id=s.append_turn(None,'first','reply',[])
    ref=db.collection('conversations').document(id)
    original=ref.get().to_dict()
    original['messages']=[{'role':'user','content':'x','timestamp':'2026-01-01','tools_used':[]}] * 200
    ref.set(original)
    with pytest.raises(HTTPException) as e:s.append_turn(id,'new','reply',[])
    assert e.value.status_code==409
    assert ref.get().to_dict()==original


def test_utf8_capacity_is_checked_not_only_message_count(db):
    s=service()
    messages=[{'role':'user','content':'한'*4000} for _ in range(80)]
    with pytest.raises(HTTPException) as e:s.save_conversation(None,messages)
    assert e.value.status_code==409
    assert not db.store
