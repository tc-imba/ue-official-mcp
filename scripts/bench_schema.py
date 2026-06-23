"""Quick benchmark: time to retrieve a toolset's schema via live MCP vs. local file.

Both paths produce the same end result the agent uses (the toolset's tools + their
input/output JSON schemas). We measure end-to-end on a few toolsets of varying size.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

ENDPOINT = "http://127.0.0.1:8001/mcp"
REFS = Path(__file__).resolve().parent.parent / "skills" / "ue-official-mcp-5.8.0" / "references" / "toolsets"

# small / medium / large / huge toolset names (by tool count)
TARGETS = [
    "PluginToolset.PluginToolset",
    "editor_toolset.toolsets.scene.SceneTools",
    "editor_toolset.toolsets.blueprint.BlueprintTools",
    "animation_toolset.toolsets.sequencer.SequencerTools",
]


async def time_mcp(targets: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    async with streamablehttp_client(ENDPOINT) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # warm the connection
            await session.call_tool("list_toolsets", {})
            for name in targets:
                t0 = time.perf_counter()
                await session.call_tool("describe_toolset", {"toolset_name": name})
                out[name] = time.perf_counter() - t0
    return out


def time_file(targets: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for name in targets:
        p = REFS / f"{name}.md"
        t0 = time.perf_counter()
        _ = p.read_text(encoding="utf-8")
        out[name] = time.perf_counter() - t0
    return out


def main() -> None:
    mcp_times = asyncio.run(time_mcp(TARGETS))
    file_times = time_file(TARGETS)
    sizes = {n: (REFS / f"{n}.md").stat().st_size for n in TARGETS}
    print(f"{'toolset':<60} {'tools':>5} {'kb':>7} {'mcp_ms':>9} {'file_ms':>9} {'ratio':>7}")
    print("-" * 110)
    # short tool counts from the file headers
    for n in TARGETS:
        size_kb = sizes[n] / 1024
        m = mcp_times[n] * 1000
        f = file_times[n] * 1000
        ratio = m / f if f > 0 else float("inf")
        print(f"{n:<60} {'':>5} {size_kb:>7.1f} {m:>9.2f} {f:>9.3f} {ratio:>7.0f}x")


if __name__ == "__main__":
    main()
