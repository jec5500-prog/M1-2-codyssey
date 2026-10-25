import importlib
import json
import httpx
import pytest
from fastapi import HTTPException
from openai import OpenAI


def ai():
    try:return importlib.import_module('services.ai_chat')
    except ModuleNotFoundError:pytest.fail('Bounded AI chat service is missing')


def completion(content='평균은 25도입니다.',tool_calls=None):
    return {'id':'chatcmpl-test','object':'chat.completion','created':1,'model':'gpt-4o-mini',
            'choices':[{'index':0,'finish_reason':'tool_calls' if tool_calls else 'stop',
                        'message':{'role':'assistant','content':content,'tool_calls':tool_calls}}],
            'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}}


def tool_call(name='get_data_summary',arguments='{}',id='call-1'):
    return {'id':id,'type':'function','function':{'name':name,'arguments':arguments}}


def configure(monkeypatch,responses):
    mod=ai();requests=[]
    def handler(request):
        requests.append(json.loads(request.content))
        value=responses[min(len(requests)-1,len(responses)-1)]
        if isinstance(value,Exception):raise value
        if isinstance(value,int):return httpx.Response(value,json={'error':{'message':'private upstream detail','type':'test_error'}})
        return httpx.Response(200,json=value)
    sdk=OpenAI(api_key='test-key',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(mod,'_get_openai',lambda:sdk)
    return mod,requests


def test_chat_injects_real_summary_and_saves_turn(client,db,monkeypatch):
    client.post('/api/data',json={'date':'2026-06-01','value':25})
    mod,requests=configure(monkeypatch,[completion()])
    r=client.post('/api/chat',json={'message':'요약해줘'})
    assert r.status_code==200
    payload=requests[0]
    assert '25.0' in payload['messages'][0]['content']
    assert payload['messages'][0]['role']=='system'
    assert payload['max_completion_tokens']==600
    assert client.get('/api/conversations/'+r.json()['conversation_id']).json()['message_count']==2


def test_tool_call_returns_data_then_final_reply(client,monkeypatch):
    client.post('/api/data',json={'date':'2026-06-01','value':25})
    _,requests=configure(monkeypatch,[completion(None,[tool_call()]),completion()])
    r=client.post('/api/chat',json={'message':'6월 데이터를 요약해줘'})
    assert r.status_code==200
    assert r.json()['tool_calls_used']==['get_data_summary']
    tool_message=requests[1]['messages'][-1]
    assert tool_message['role']=='tool'
    assert json.loads(tool_message['content'])['average']==25


def test_tool_loop_has_finite_rounds(client,monkeypatch):
    _,requests=configure(monkeypatch,[completion(None,[tool_call()])])
    r=client.post('/api/chat',json={'message':'loop'})
    assert r.status_code==502
    assert len(requests)==4
    assert requests[-1]['tool_choice']=='none'


@pytest.mark.parametrize('status,expected',[(401,502),(429,429),(500,502)])
def test_upstream_error_is_sanitized_and_never_saved(client,db,monkeypatch,status,expected):
    configure(monkeypatch,[status])
    r=client.post('/api/chat',json={'message':'질문'})
    assert r.status_code==expected
    assert 'private upstream' not in r.text
    assert not [key for key in db.store if key[0]=='conversations']


def test_history_window_preserves_full_storage(client,monkeypatch):
    from services import conversations
    id=conversations.save_conversation('history',[{'role':'user' if i%2==0 else 'assistant','content':f'm{i}'} for i in range(24)])['id']
    _,requests=configure(monkeypatch,[completion()])
    r=client.post('/api/chat',json={'message':'next','conversation_id':id})
    assert r.status_code==200
    assert len(requests[0]['messages'])==22
    assert requests[0]['messages'][1]['content']=='m4'
    assert conversations.get_conversation(id)['message_count']==26


def test_deadline_prevents_late_reply_storage(client,db,monkeypatch):
    mod,requests=configure(monkeypatch,[completion()])
    ticks=iter([0,0,0,100,100,100])
    monkeypatch.setattr(mod,'clock',lambda:next(ticks,100))
    r=client.post('/api/chat',json={'message':'slow'})
    assert r.status_code==504
    assert not [key for key in db.store if key[0]=='conversations']


def test_chat_rate_limit_returns_429_after_six_requests(client,monkeypatch):
    configure(monkeypatch,[completion()])
    responses=[client.post('/api/chat',json={'message':'질문'}) for _ in range(7)]
    assert [r.status_code for r in responses]==[200]*6+[429]
    assert 'retry-after' in responses[-1].headers


def test_tools_reject_unknown_tools_and_invalid_period(db):
    try:mod=importlib.import_module('services.tools')
    except ModuleNotFoundError:pytest.fail('Validated AI tool adapter is missing')
    assert 'error' in mod.execute_tool('unknown',{})
    assert 'error' in mod.execute_tool('get_data_summary',{'start_date':'2026-02-30'})
    assert 'error' in mod.execute_tool('get_data_summary',{'start_date':'2026-09-01','end_date':'2026-06-01'})


def test_chat_passes_total_deadline_to_storage_and_checks_late_result(client,monkeypatch):
    mod,_=configure(monkeypatch,[completion()])
    tick=[100]
    monkeypatch.setattr(mod,'clock',lambda:tick[0])
    captured=[]
    def delayed_storage(*args,**kwargs):
        captured.append(kwargs.get('deadline'))
        tick[0]=250
        return 'saved-id'
    monkeypatch.setattr(mod.conversations,'append_turn',delayed_storage)
    response=client.post('/api/chat',json={'message':'slow save'})
    assert captured==[190]
    assert response.status_code==504
