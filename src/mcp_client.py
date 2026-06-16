from typing import List, Tuple, Optional
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.config import MCP_TOOL_ALLOWLIST, PROJECT_ROOT

# Absolute path to the MCP server script, resolved from the project root.
_MCP_SERVER_PATH = str(PROJECT_ROOT / "mcp_server" / "server.py")


def is_allowed_tool(tool_name: str) -> bool:
    """Return True if the tool name is in the allowlist."""
    return tool_name in MCP_TOOL_ALLOWLIST


async def connect_mcp_server() -> Tuple[Optional[MultiServerMCPClient], List]:
    """Start the MCP server subprocess, open a session, and return (client, allowed_tools).

    The caller must keep a reference to the returned client to keep the
    subprocess connection alive for the lifetime of the session.

    Returns (None, []) if the server is unavailable.
    """
    # MCP (Model Context Protocol) lets external servers expose tools the agent
    # can call at runtime — here it simulates a CRM / order-management system.
    # In production, swap mcp_server/server.py for a real CRM endpoint.
    try:
        client = MultiServerMCPClient(
            {
                "customer_support_crm": {
                    "command": sys.executable,
                    "args": [_MCP_SERVER_PATH],
                    "transport": "stdio",
                }
            }
        )

        discovered = await client.get_tools()

        permitted = [t for t in discovered if is_allowed_tool(t.name)]
        blocked = [t.name for t in discovered if not is_allowed_tool(t.name)]

        print(f"MCP server connected. {len(discovered)} tool(s) discovered, {len(permitted)} permitted:")
        for t in permitted:
            print(f"  [allowed]  {t.name} — {t.description[:70]}")
        if blocked:
            print(f"  [blocked]  {blocked}  (not in allowlist)")

        return client, permitted

    except Exception as exc:
        print(f"Warning: MCP server unavailable ({exc}). Continuing without MCP tools.")
        return None, []
