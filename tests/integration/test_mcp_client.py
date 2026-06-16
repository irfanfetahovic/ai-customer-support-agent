"""
Integration tests for src/mcp_client.py.

These tests start the real MCP server subprocess via connect_mcp_server()
and verify end-to-end behaviour: connection, tool discovery, allowlist
filtering, and actual tool invocation.

No external API keys are required — the MCP server uses simulated data.
"""

import asyncio
import json

import pytest

from src.config import MCP_TOOL_ALLOWLIST
from src.mcp_client import connect_mcp_server


@pytest.fixture(scope="module")
def mcp_connection():
    """Start the MCP server once for the whole module and return (client, tools)."""
    client, tools = asyncio.run(connect_mcp_server())
    # asyncio.run is needed because connect_mcp_server is async, but pytest fixture mcp_connection is synchronous.
    if client is None:
        pytest.skip("MCP server failed to start — check that mcp_server/server.py is present")
    return client, tools


class TestMcpServerConnection:
    # pytest.mark.anyio allows executing async functions in pytest.
    @pytest.mark.anyio
    async def test_returns_client_and_tools(self, mcp_connection):
        client, tools = mcp_connection
        assert client is not None
        assert isinstance(tools, list)

    @pytest.mark.anyio
    async def test_both_allowlisted_tools_are_returned(self, mcp_connection):
        _, tools = mcp_connection
        tool_names = {t.name for t in tools}
        assert MCP_TOOL_ALLOWLIST == tool_names

    @pytest.mark.anyio
    async def test_no_tools_outside_allowlist_returned(self, mcp_connection):
        _, tools = mcp_connection
        for tool in tools:
            assert tool.name in MCP_TOOL_ALLOWLIST, f"Unexpected tool in results: {tool.name}"

    @pytest.mark.anyio
    async def test_tools_have_descriptions(self, mcp_connection):
        _, tools = mcp_connection
        for tool in tools:
            assert tool.description and len(tool.description) > 0


class TestMcpToolInvocation:
    def _parse(self, result) -> dict:
        """Extract JSON from tool result (LangChain wraps output in a content list)."""
        if isinstance(result, list):
            text = result[0]["text"]
        else:
            text = result
        return json.loads(text)

    @pytest.mark.anyio
    async def test_lookup_order_status_known_order(self, mcp_connection):
        _, tools = mcp_connection
        tool = next(t for t in tools if t.name == "lookup_order_status")
        result = await tool.ainvoke({"order_id": "ORD-1001"})
        data = self._parse(result)
        assert "error" not in data
        assert data["status"] == "Delivered"
        assert "item" in data

    @pytest.mark.anyio
    async def test_lookup_order_status_unknown_order_returns_error(self, mcp_connection):
        _, tools = mcp_connection
        tool = next(t for t in tools if t.name == "lookup_order_status")
        result = await tool.ainvoke({"order_id": "ORD-9999"})
        data = self._parse(result)
        assert "error" in data

    @pytest.mark.anyio
    async def test_lookup_customer_profile_known_customer(self, mcp_connection):
        _, tools = mcp_connection
        tool = next(t for t in tools if t.name == "lookup_customer_profile")
        result = await tool.ainvoke({"customer_id": "C001"})
        data = self._parse(result)
        assert "error" not in data
        assert data["name"] == "Alice Johnson"
        assert "subscription_tier" in data

    @pytest.mark.anyio
    async def test_lookup_customer_profile_unknown_customer_returns_error(self, mcp_connection):
        _, tools = mcp_connection
        tool = next(t for t in tools if t.name == "lookup_customer_profile")
        result = await tool.ainvoke({"customer_id": "C999"})
        data = self._parse(result)
        assert "error" in data

    @pytest.mark.anyio
    async def test_order_id_lookup_is_case_insensitive(self, mcp_connection):
        _, tools = mcp_connection
        tool = next(t for t in tools if t.name == "lookup_order_status")
        result = await tool.ainvoke({"order_id": "ord-1002"})
        data = self._parse(result)
        assert "error" not in data
        assert data["status"] == "In Transit"
