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

