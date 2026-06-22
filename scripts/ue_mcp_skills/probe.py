"""Probe a live official UE MCP server over streamable HTTP.

Tool Search is on, so the server exposes 3 meta-tools (`list_toolsets`,
`describe_toolset`, `call_tool`). We call `list_toolsets`, parse the toolset names,
then `describe_toolset` each one and keep the validated results.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# A toolset name is a dotted identifier at the start of a top-level "- " bullet,
# e.g. "- EditorToolset.LogsToolset: ...". Requiring a dot avoids matching prose
# bullets inside multi-line descriptions (e.g. "- GetAssetDiscoveryInfo: ...").
# Any false positive that slips through is dropped by describe_toolset validation.
_TOOLSET_LINE = re.compile(r"^-\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)\s*:", re.MULTILINE)


def _result_text(result: Any) -> str:
    """Concatenate the text content blocks of a CallToolResult."""
    parts = []
    for block in (getattr(result, "content", None) or []):
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts)


def _result_json(result: Any) -> Any:
    """Prefer structured content; fall back to parsing the text block as JSON."""
    structured = getattr(result, "structuredContent", None)
    if structured:
        return structured
    return json.loads(_result_text(result).strip())


async def _open_session(endpoint: str):
    return streamablehttp_client(endpoint)


async def _probe_async(endpoint: str) -> dict:
    async with streamablehttp_client(endpoint) as (read, write, _):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            server = {}
            info = getattr(init, "serverInfo", None)
            if info is not None:
                server = {
                    "name": getattr(info, "name", ""),
                    "version": getattr(info, "version", ""),
                }

            listing = await session.call_tool("list_toolsets", {})
            candidates = sorted(set(_TOOLSET_LINE.findall(_result_text(listing))))

            toolsets: list[dict] = []
            skipped: list[str] = []
            for name in candidates:
                try:
                    described = await session.call_tool(
                        "describe_toolset", {"toolset_name": name}
                    )
                    if getattr(described, "isError", False):
                        skipped.append(name)
                        continue
                    data = _result_json(described)
                    if not isinstance(data, dict) or "tools" not in data:
                        skipped.append(name)
                        continue
                    data.setdefault("name", name)
                    toolsets.append(data)
                except Exception:  # noqa: BLE001 - any failure means "not a real toolset"
                    skipped.append(name)

            toolsets.sort(key=lambda t: t.get("name", ""))
            return {
                "endpoint": endpoint,
                "server": server,
                "toolset_count": len(toolsets),
                "tool_count": sum(len(t.get("tools", []) or []) for t in toolsets),
                "skipped_candidates": skipped,
                "toolsets": toolsets,
            }


async def _ping_async(endpoint: str) -> bool:
    async with streamablehttp_client(endpoint) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return True


def probe(endpoint: str) -> dict:
    """Probe the server and return the structured catalog (sync wrapper)."""
    return asyncio.run(_probe_async(endpoint))


def ping(endpoint: str) -> bool:
    """Return True if an MCP handshake succeeds against the endpoint."""
    try:
        return asyncio.run(_ping_async(endpoint))
    except Exception:  # noqa: BLE001
        return False
