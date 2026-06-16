from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import MCP_TOOL_ALLOWLIST
from src.mcp_client import connect_mcp_server, is_allowed_tool


class TestIsAllowedTool:
    def test_allowlisted_tools_return_true(self):
        for name in MCP_TOOL_ALLOWLIST:
            assert is_allowed_tool(name) is True

    def test_unknown_tool_returns_false(self):
        assert is_allowed_tool("delete_all_records") is False

    def test_empty_string_returns_false(self):
        assert is_allowed_tool("") is False

    def test_partial_name_returns_false(self):
        # "lookup_customer" is a prefix of an allowed name but must not pass
        assert is_allowed_tool("lookup_customer") is False

    def test_case_sensitive(self):
        # Allowlist entries are lowercase; uppercase variant must not pass
        assert is_allowed_tool("LOOKUP_ORDER_STATUS") is False


class TestConnectMcpServer:
    def _make_tool(self, name: str) -> MagicMock:
        tool = MagicMock()
        tool.name = name
        tool.description = f"Description for {name}"
        return tool

    @pytest.mark.anyio
    async def test_returns_none_and_empty_list_on_exception(self):
        # replaces MultiServerMCPClient with a mock that raises an exception when get_tools is called
        with patch("src.mcp_client.MultiServerMCPClient") as MockClient:
            # MockClient.return_value is the instance returned when MultiServerMCPClient() is called
            # MockClient.return_value.get_tools is replacing client.get_tools
            MockClient.return_value.get_tools = AsyncMock(
                side_effect=Exception("server not found")
            )

            client, tools = await connect_mcp_server()

        assert client is None
        assert tools == []

    @pytest.mark.anyio
    async def test_returns_client_and_permitted_tools_on_success(self):
        allowed_tool = self._make_tool("lookup_order_status")

        with patch("src.mcp_client.MultiServerMCPClient") as MockClient:
            instance = MockClient.return_value
            instance.get_tools = AsyncMock(return_value=[allowed_tool])

            client, tools = await connect_mcp_server()

        assert client is instance
        assert len(tools) == 1
        assert tools[0].name == "lookup_order_status"

    @pytest.mark.anyio
    async def test_blocked_tools_are_filtered_out(self):
        allowed_tool = self._make_tool("lookup_customer_profile")
        blocked_tool = self._make_tool("delete_customer_record")

        with patch("src.mcp_client.MultiServerMCPClient") as MockClient:
            instance = MockClient.return_value
            instance.get_tools = AsyncMock(return_value=[allowed_tool, blocked_tool])

            client, tools = await connect_mcp_server()

        tool_names = [t.name for t in tools]
        assert "lookup_customer_profile" in tool_names
        assert "delete_customer_record" not in tool_names

    @pytest.mark.anyio
    async def test_all_tools_blocked_returns_client_with_empty_list(self):
        blocked_tool = self._make_tool("drop_database")

        with patch("src.mcp_client.MultiServerMCPClient") as MockClient:
            instance = MockClient.return_value
            instance.get_tools = AsyncMock(return_value=[blocked_tool])

            client, tools = await connect_mcp_server()

        assert client is instance
        assert tools == []

    @pytest.mark.anyio
    async def test_no_tools_discovered_returns_empty_list(self):
        with patch("src.mcp_client.MultiServerMCPClient") as MockClient:
            instance = MockClient.return_value
            instance.get_tools = AsyncMock(return_value=[])

            client, tools = await connect_mcp_server()

        assert client is instance
        assert tools == []
