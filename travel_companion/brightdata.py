"""Bright Data via its hosted remote MCP server.

No install, no local process — one streamable-HTTP URL with the token in the
query string. The MCPClient context manager owns the connection: tools taken
from it are dead outside the `with` block, which is the single most common way
this breaks.
"""

from __future__ import annotations

from mcp.client.streamable_http import streamable_http_client
from strands.tools.mcp import MCPClient

from .config import BRIGHTDATA_MCP_URL


def client() -> MCPClient:
    # NB: in mcp >= 2.x the symbol is `streamable_http_client`; older tutorials
    # import `streamablehttp_client`, which no longer exists.
    return MCPClient(lambda: streamable_http_client(BRIGHTDATA_MCP_URL))


def search_sync(query: str, limit: int = 5) -> list[str]:
    """One-shot search used by the ingest path (build the world dataset).

    The agent's *live* path doesn't go through here — it calls the Bright Data
    MCP tools directly, so the tool call shows up in the trace.
    """
    with client() as bright:
        tools = {t.tool_name: t for t in bright.list_tools_sync()}
        name = next(
            (n for n in ("search_engine", "scrape_as_markdown") if n in tools), None
        )
        if name is None:
            raise RuntimeError(f"no search tool on the MCP server; saw: {list(tools)}")

        result = bright.call_tool_sync(
            tool_use_id="ingest-search",
            name=name,
            arguments={"query": query} if name == "search_engine" else {"url": query},
        )

    blocks = [c.get("text", "") for c in result.get("content", []) if "text" in c]
    return [b for b in blocks if b.strip()][:limit]
