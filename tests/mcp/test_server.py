import asyncio
import importlib

import pytest


def server_module():
    try:return importlib.import_module('integrations.mcp.server')
    except ModuleNotFoundError:pytest.fail('Independent MCP API adapter is missing')


def test_mcp_lists_read_only_tools_and_maps_period(monkeypatch):
    mod=server_module();calls=[]
    def fetch(path,params):
        calls.append((path,params))
        return {'count':30,'average':23.5}
    monkeypatch.setattr(mod,'read_api',fetch)
    from mcp import Client
    async def check():
        async with Client(mod.server) as client:
            tools=(await client.list_tools()).tools
            assert {t.name for t in tools}=={'get_data_summary','query_data_points'}
            result=await client.call_tool('get_data_summary',{'start_date':'2026-06-01','end_date':'2026-06-30'})
            assert not result.is_error
            assert result.structured_content['average']==23.5
    asyncio.run(check())
    assert calls==[('/api/data/summary',{'start':'2026-06-01','end':'2026-06-30'})]


def test_mcp_invalid_period_never_calls_api(monkeypatch):
    mod=server_module()
    def unexpected(*args):pytest.fail('Invalid period must not reach API')
    monkeypatch.setattr(mod,'read_api',unexpected)
    from mcp import Client
    async def check():
        async with Client(mod.server) as client:
            r=await client.call_tool('get_data_summary',{'start_date':'2026-02-30'})
            assert r.is_error
            r=await client.call_tool('query_data_points',{'limit':999})
            assert r.is_error
    asyncio.run(check())


def test_mcp_points_returns_structured_records(monkeypatch):
    mod=server_module();calls=[]
    def fetch(path,params):
        calls.append((path,params));return [{'id':'a','date':'2026-09-30','value':20.7,'memo':'서울'}]
    monkeypatch.setattr(mod,'read_api',fetch)
    from mcp import Client
    async def check():
        async with Client(mod.server) as client:
            r=await client.call_tool('query_data_points',{'limit':1,'order':'desc'})
            assert r.structured_content['points'][0]['value']==20.7
    asyncio.run(check())
    assert calls[0][0]=='/api/data'
    assert calls[0][1]['limit']==1
