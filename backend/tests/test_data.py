import pytest


@pytest.mark.parametrize('value', ['NaN','Infinity','-Infinity'])
def test_nonfinite_values_are_rejected_before_storage(client,db,value):
    r=client.post('/api/data',json={'date':'2026-06-01','value':value})
    assert r.status_code == 422
    assert not db.store


@pytest.mark.parametrize('query', ['start=2026-02-30','end=2026-13-01','start=2026-08-01&end=2026-06-01'])
@pytest.mark.parametrize('path', ['/api/data','/api/data/summary'])
def test_bad_period_is_rejected(client,query,path):
    assert client.get(f'{path}?{query}').status_code == 422


def test_crud_and_summary_share_required_data_collection(client,db):
    r=client.post('/api/data',json={'date':'2026-06-01','value':-2,'memo':'test'})
    assert r.status_code == 201
    id=r.json()['id']
    assert ('data',id) in db.store
    assert client.put(f'/api/data/{id}',json={'value':4}).json()['value'] == 4
    assert client.get('/api/data/summary').json()['average'] == 4
    assert len(client.get('/api/data').json()) == 1
    assert client.delete(f'/api/data/{id}').status_code == 204
    assert client.get(f'/api/data/{id}').status_code == 404
    assert client.put(f'/api/data/{id}',json={'value':2}).status_code == 404
    assert client.delete(f'/api/data/{id}').status_code == 404


def test_export_neutralizes_formula_memo(client):
    client.post('/api/data',json={'date':'2026-06-01','value':4,'memo':'=1+2'})
    r=client.get('/api/data/export/csv')
    assert r.status_code == 200
    assert "'=1+2" in r.text
    assert 'attachment' in r.headers['content-disposition']


@pytest.mark.parametrize('value', [1e308,-1e308,1e12+1,-1e12-1])
def test_values_that_can_overflow_summary_are_rejected(client,db,value):
    response=client.post('/api/data',json={'date':'2026-06-01','value':value})
    assert response.status_code==422
    assert not db.store


@pytest.mark.parametrize('literal',['1e999','NaN','Infinity','-Infinity'])
def test_raw_nonfinite_json_receives_safe_validation_error(client,literal):
    response=client.post('/api/data',content='{"date":"2026-06-01","value":'+literal+'}',headers={'Content-Type':'application/json'})
    assert response.status_code==422
    assert response.json()['detail'][0]['loc'][-1]=='value'

def test_subnormal_start_value_does_not_overflow_trend_json(client):
    import json
    from services.data_summary import compute_summary
    json.dumps(compute_summary([{'date':'2026-01-01','value':1e-320},{'date':'2026-01-02','value':1}]),allow_nan=False)
    for day,value in [('2026-01-01',1e-320),('2026-01-02',1)]:
        assert client.post('/api/data',json={'date':day,'value':value}).status_code==201
    result=client.get('/api/data/summary')
    assert result.status_code==200
    assert result.json()['trend']['change_percent'] is None

