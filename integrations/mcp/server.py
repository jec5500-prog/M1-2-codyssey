"""Run with Python over stdio. Only API_BASE_URL is needed, never server keys."""
from datetime import datetime
import os
import re
from typing import Annotated, Literal, Any
from urllib.parse import urlsplit

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

server=MCPServer('Codyssey Data Assistant',instructions='Use stored data before answering numeric questions. These tools only read the same FastAPI service as the web UI.')
readonly=ToolAnnotations(read_only_hint=True,open_world_hint=False)


def _period(start: str | None,end: str | None) -> dict:
    try:
        for v in (start,end):
            if v is not None:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):raise ValueError()
                datetime.strptime(v,'%Y-%m-%d')
        if start and end and start>end:raise ValueError()
    except ValueError:
        raise ToolError('날짜는 존재하는 YYYY-MM-DD이어야 하며 시작일은 종료일보다 늦을 수 없습니다.')
    return {k:v for k,v in {'start':start,'end':end}.items() if v is not None}


def read_api(path: str,params: dict):
    base=os.getenv('API_BASE_URL','https://m1-2-codyssey.onrender.com').rstrip('/')
    parsed=urlsplit(base)
    if (parsed.scheme not in ('http','https') or not parsed.hostname or parsed.path or parsed.query
            or parsed.fragment or parsed.username or parsed.password
            or (parsed.scheme=='http' and parsed.hostname not in ('localhost','127.0.0.1','::1'))):
        raise ToolError('API_BASE_URL은 HTTPS origin 또는 로컬 HTTP origin이어야 합니다.')
    try:
        with httpx.Client(timeout=httpx.Timeout(90,connect=10)) as client:
            response=client.get(base+path,params=params)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError,ValueError):
        raise ToolError('API 조회에 실패했습니다. API 주소·서버 상태·조회 조건을 확인하세요.')


@server.tool(annotations=readonly)
def get_data_summary(start_date: str | None=None,end_date: str | None=None) -> dict[str,Any]:
    """기간별 개수·평균·최소·최대·추세를 같은 Render API에서 조회합니다."""
    return read_api('/api/data/summary',_period(start_date,end_date))


@server.tool(annotations=readonly)
def query_data_points(start_date: str | None=None,end_date: str | None=None,
                      limit: Annotated[int,Field(ge=1,le=200)]=50,
                      order: Literal['asc','desc']='asc') -> dict[str,Any]:
    """날짜·개수 조건으로 실제 데이터 조회. 최근 데이터는 order=desc."""
    params={**_period(start_date,end_date),'limit':limit,'order':order}
    points=read_api('/api/data',params)
    return {'count':len(points),'points':points}


if __name__=='__main__':
    server.run(transport='stdio')
