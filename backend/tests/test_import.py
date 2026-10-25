import importlib
import pytest


def importer():
    try: return importlib.import_module('scripts.import_data')
    except ModuleNotFoundError: pytest.fail('CSV validation and repeat-safe importer is missing')


def test_import_is_repeat_safe_without_deleting_user_data(db):
    db.project='m1-2-cody'
    db.collection('data').document('personal').set({'date':'2026-01-01','value':1,'memo':'keep'})
    rows=[{'date':'2026-06-01','value':20.5,'memo':'source'}]
    m=importer()
    assert m.import_rows(rows,db)['created']==1
    assert m.import_rows(rows,db)['created']==0
    assert len(db.store)==2
    assert db.collection('data').document('personal').get().to_dict()['memo']=='keep'


def test_import_rejects_wrong_project(db):
    db.project='another-project'
    with pytest.raises(ValueError,match='project'):
        importer().import_rows([{'date':'2026-06-01','value':1}],db)
    assert not db.store


def test_csv_rejects_duplicate_dates_and_nonfinite_values(tmp_path):
    p=tmp_path/'sample.csv'
    p.write_text('date,value,memo\n2026-06-01,2,a\n2026-06-01,3,b\n')
    with pytest.raises(ValueError,match='duplicate'):
        importer().read_rows(p)
    p.write_text('date,value,memo\n2026-06-01,NaN,a\n')
    with pytest.raises(ValueError): importer().read_rows(p)
