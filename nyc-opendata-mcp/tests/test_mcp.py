"""MCP stdio round trip: start the server as Claude Desktop would, list tools, call two of them."""
import asyncio
import json
import os
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SRC = os.path.join(os.path.dirname(__file__), '..', 'src')


def _text(res):
    if getattr(res, 'structuredContent', None) or getattr(res, 'structured_content', None):
        return getattr(res, 'structuredContent', None) or getattr(res, 'structured_content', None)
    return json.loads(res.content[0].text)


async def _roundtrip():
    env = dict(os.environ, PYTHONPATH=SRC)
    params = StdioServerParameters(command=sys.executable, args=['-m', 'nycod.server'], env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            names = {t.name for t in tools}
            parsed = _text(await s.call_tool('nycod_parse_sr_text', {'address': '7 AVENUE AND LINCOLN PLACE, BROOKLYN, NY'}))
            brief = await s.call_tool('nycod_sr_brief', {'sr': '311-29399735', 'borough': 'Brooklyn', 'street1': '7 Avenue',
                                                         'street2': 'Lincoln Place', 'complaint_date': '2026-10-20'})
            return names, parsed, brief


def test_stdio_roundtrip():
    names, parsed, brief = asyncio.run(_roundtrip())
    assert {'nycod_sr_brief', 'nycod_workbook_briefs', 'nycod_permits_at_intersection', 'nycod_ramp_complaints'} <= names
    assert len(names) == 22
    assert parsed['address']['cross_street'] == 'LINCOLN PLACE'
    assert not getattr(brief, 'isError', getattr(brief, 'is_error', False)), brief
    b = _text(brief)
    assert sorted(b['facts']['this_sr_logged_corners']) == [1108794, 1108796]
