"""Verify the actual API; only self-created disposable records are deleted. No GPT cost."""
import argparse
import csv
import io
import json
from pathlib import Path
from uuid import uuid4

import httpx


def verify(base: str) -> dict:
    checks={}
    with httpx.Client(base_url=base,timeout=90) as c:
        for path in ('/','/health','/docs','/openapi.json'):
            r=c.get(path);r.raise_for_status();checks[path]=r.status_code
        summary=c.get('/api/data/summary');summary.raise_for_status();summary=summary.json()
        rows=c.get('/api/data',params={'limit':2000}).json()
        assert len(rows)==summary['count']>=100
        assert round(sum(p['value'] for p in rows)/len(rows),4)==summary['average']
        checks['data_summary_matches_rows']=True
        marker='API verification '+uuid4().hex
        point_id=conv_id=None
        try:
            r=c.post('/api/data',json={'date':'2026-10-25','value':23.4,'memo':marker})
            assert r.status_code==201;point_id=r.json()['id'];checks['POST /api/data']=201
            assert any(p['id']==point_id for p in c.get('/api/data',params={'order':'desc'}).json())
            checks['GET /api/data']=200
            r=c.put('/api/data/'+point_id,json={'value':24.5});assert r.status_code==200 and r.json()['value']==24.5
            checks['PUT /api/data/{id}']=200
            assert c.delete('/api/data/'+point_id).status_code==204
            assert c.get('/api/data/'+point_id).status_code==404;point_id=None
            checks['DELETE /api/data/{id}']=204
            r=c.post('/api/conversations',json={'title':marker,'messages':[{'role':'user','content':'수동 저장 검사'},{'role':'assistant','content':'검사용 기록입니다. 실제 AI 응답이 아닙니다.'}]})
            assert r.status_code==201;conv_id=r.json()['id'];checks['POST /api/conversations']=201
            assert any(v['id']==conv_id for v in c.get('/api/conversations').json());checks['GET /api/conversations']=200
            r=c.get('/api/conversations/'+conv_id);assert r.status_code==200 and r.json()['message_count']==2
            checks['GET /api/conversations/{id}']=200
            assert c.delete('/api/conversations/'+conv_id).status_code==204
            assert c.get('/api/conversations/'+conv_id).status_code==404;conv_id=None
            checks['DELETE /api/conversations/{id}']=204
            assert c.post('/api/data',json={'date':'2026-02-30','value':1}).status_code==422
            assert c.post('/api/data',content='{"date":"2026-01-01","value":1e999}',headers={'Content-Type':'application/json'}).status_code==422
            checks['invalid_input']=422
            exported=c.get('/api/data/export/csv');exported.raise_for_status()
            assert exported.content.startswith(b'\xef\xbb\xbf')
            assert len(list(csv.DictReader(io.StringIO(exported.content.decode('utf-8-sig')))))==len(rows)
            checks['csv_rows_and_bom']=True
        finally:
            if point_id:c.delete('/api/data/'+point_id)
            if conv_id:c.delete('/api/conversations/'+conv_id)
        assert c.get('/api/data/summary').json()==summary
    return {'api_base_url':base,'checks':checks,'summary':summary,'temporary_records_removed':True,'chat':'Separate capped live GPT verification; not called by this script.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--api-base-url',default='https://m1-2-codyssey.onrender.com')
    p.add_argument('--output',default='docs/test-results/api-live.json')
    args=p.parse_args();result=verify(args.api_base_url)
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'checks':len(result['checks']),'count':result['summary']['count'],'temporary_records_removed':True}))
