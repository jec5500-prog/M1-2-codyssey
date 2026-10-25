"""Verify an independent stdio client/server against the deployed HTTP API."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

import httpx
from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def verify(base: str) -> dict:
    command=StdioServerParameters(command=sys.executable,
        args=[str(Path(__file__).resolve().parents[1]/'integrations'/'mcp'/'server.py')],
        env={'API_BASE_URL':base,'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1'})
    async with Client(command,read_timeout_seconds=100) as client:
        listed=await client.list_tools()
        summary=await client.call_tool('get_data_summary',{})
        recent=await client.call_tool('query_data_points',{'limit':3,'order':'desc'})
        assert not summary.is_error and not recent.is_error
        with httpx.Client(timeout=90) as http:
            direct=http.get(base.rstrip('/')+'/api/data/summary');direct.raise_for_status()
        assert summary.structured_content==direct.json()
        assert summary.structured_content['count']>=100
        assert recent.structured_content['count']==3
        return {'api_base_url':base,'server':client.server_info.name,'protocol':client.protocol_version,
                'tools':[t.name for t in listed.tools], 'summary_matches_http_api':True,
                'summary':summary.structured_content,'recent':recent.structured_content}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-base-url',default='https://m1-2-codyssey.onrender.com')
    parser.add_argument('--output',default='docs/test-results/mcp-live.json')
    args=parser.parse_args()
    result=asyncio.run(verify(args.api_base_url))
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'server':result['server'],'protocol':result['protocol'],'count':result['summary']['count'],'matches_api':True}))
