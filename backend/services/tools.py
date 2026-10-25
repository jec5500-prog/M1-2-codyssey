"""Read-only GPT tool adapters with the same validation as HTTP data queries."""
import logging
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from routers.data import fetch_points, validate_period
from services.data_summary import compute_summary

logger=logging.getLogger(__name__)


class Period(BaseModel):
    model_config=ConfigDict(extra='forbid')
    start_date: str | None = None
    end_date: str | None = None


class PointsArgs(Period):
    order: Literal['asc','desc']='asc'
    limit: int=Field(50,ge=1,le=200)


class ExtremeArgs(Period):
    mode: Literal['highest','lowest']
    n: int=Field(5,ge=1,le=50)


def execute_tool(name: str,args: dict) -> dict:
    try:
        classes={'query_data_points':PointsArgs,'get_data_summary':Period,'get_extreme_points':ExtremeArgs}
        if name not in classes:return {'error':'알 수 없는 도구입니다.'}
        p=classes[name].model_validate(args)
        validate_period(p.start_date,p.end_date)
        if name=='get_data_summary':return compute_summary(fetch_points(p.start_date,p.end_date))
        if name=='query_data_points':
            pts=fetch_points(p.start_date,p.end_date,p.limit,descending=p.order=='desc')
            return {'count':len(pts),'points':[{k:v for k,v in p.items() if k!='id'} for p in pts]}
        pts=fetch_points(p.start_date,p.end_date)
        pts.sort(key=lambda v:v['value'],reverse=p.mode=='highest')
        return {'mode':p.mode,'points':[{k:v for k,v in row.items() if k!='id'} for row in pts[:p.n]]}
    except (ValidationError,HTTPException,ValueError):
        return {'error':'도구의 날짜·기간·개수 인자가 올바르지 않습니다.'}
    except Exception:
        logger.error('Data tool failed: %s',name)
        return {'error':'데이터를 조회하지 못했습니다. 수치를 추측하지 말고 오류를 알려주세요.'}


def _schema(name,description,model):
    schema=model.model_json_schema()
    schema.pop('title',None)
    return {'type':'function','function':{'name':name,'description':description,'parameters':schema}}


TOOLS=[
    _schema('query_data_points','특정 날짜/기간의 실제 시계열 값 조회. 최근 N건은 order=desc.',PointsArgs),
    _schema('get_data_summary','지정 기간의 데이터 개수·평균·최소·최대·추세. 전체 요약과 다른 기간을 비교할 때 사용.',Period),
    _schema('get_extreme_points','값이 가장 높거나 낮은 실제 날짜/값을 N개 조회.',ExtremeArgs),
]
