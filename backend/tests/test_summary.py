import pytest

from routers.data import compute_summary


@pytest.mark.parametrize('values,want', [([], 'insufficient'),([2],'insufficient'),([1,2,3],'up'),([3,2,1],'down'),([0,0,0],'flat'),([-3,-2,-1],'up')])
def test_trend_including_zero_and_negative_values(values,want):
    pts=[{'date':f'2026-06-{i+1:02d}','value':v,'memo':''} for i,v in enumerate(values)]
    assert compute_summary(pts)['trend']['direction'] == want


def test_unsorted_points_and_duplicate_dates_are_counted():
    r=compute_summary([
        {'date':'2026-06-03','value':8,'memo':''},
        {'date':'2026-06-01','value':-2,'memo':''},
        {'date':'2026-06-01','value':3,'memo':''},
    ])
    assert r['count']==3
    assert r['total']==9
    assert r['average']==3
    assert r['minimum']['value']==-2
    assert r['maximum']['value']==8
    assert r['first_date']=='2026-06-01'
    assert r['last_date']=='2026-06-03'
