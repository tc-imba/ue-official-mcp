# Design — ue-official-mcp-skills

Approved design record (brainstormed before implementation). The README is the user-facing doc;
this captures the *why* and the decisions for contributors.

## Goal

A standalone, open-source toolkit that regenerates and publishes the `ue-official-mcp` reference
docs by probing a live UE 5.8 editor, packaged with the portable skill and an empty MCP-enabled
project as the probe target.

## Decisions (and the alternatives rejected)

| Decision | Chosen | Why / alternatives |
|---|---|---|
| Purpose | Shareable open-source toolkit | (vs personal source-of-truth, vs scratch sandbox) — implies git, README, MIT, clean separation from any host project. |
| Doc structure | **Hybrid**: auto raw per-toolset catalog + curated domain files + flagged `uncategorized` | Raw guarantees completeness & zero staleness; curated gives navigation. (vs raw-only = flat; vs curated-only = manual mapping breaks on new toolsets.) |
| Sync model | Connect to a running editor by default; optional `--launch` (GUI windowed, no-focus) | The official server needs a running editor; UE is launched GUI-only here, never headless. |
| Stack | Python + official `mcp` SDK + mkdocs-material, managed by `uv` | Matches the UE/Monolith/host-repo conventions. (vs Node/TS = diverges from the Python/UE ecosystem; vs shell+curl = fragile SSE/JSON-RPC by hand on Windows.) |

## Architecture

- **`skill/`** is both the portable skill **and** the mkdocs `docs_dir` (DRY: one copy of the Markdown).
- **`scripts/ue_mcp_skills/`**
  - `probe.py` — `mcp` SDK streamable-HTTP client: `initialize` → call meta-tool `list_toolsets`
    → `describe_toolset` per toolset → assemble a structured catalog → `cache/probe.json`.
    Toolset names are parsed with a dotted-identifier regex and **validated** by a successful
    `describe_toolset` (drops false positives from prose bullets in the listing).
  - `generate.py` — pure function of `cache/probe.json` + `toolset_map.yaml`. Deterministic
    (stable-sorted) so re-runs produce clean git diffs. Emits raw per-toolset files, curated
    domain files, the two index pages, and `official-uncategorized.md`.
  - `launch.py` — locates UE 5.8 (`--engine` / `UE_ENGINE_PATH` / Windows registry / default
    install path) and launches the editor GUI windowed without stealing focus, then polls the
    endpoint until the MCP handshake succeeds.
  - `cli.py` — `typer` app: `sync`, `generate`, `build`.
- **`project/UeMcpProbe.uproject`** — Blueprint-only (no `Source/`, no compile), `ModelContextProtocol`
  + `AllToolsets` enabled.

## Non-goals (YAGNI)

Headless UE; auto-publish/hosting; feeding generated docs back into any host project (clean
separation); a live-probe CI (CI can only rebuild from the committed `cache/probe.json`).

## Testing

End-to-end against a running editor: `uv sync` → `sync --endpoint <live>` (expects ~50+ toolsets /
~800+ tools) → `build` (`mkdocs build --strict` clean) → `generate` from cache (offline path).
`--launch` is implemented but verified only for path-resolution, not a live spawn.
