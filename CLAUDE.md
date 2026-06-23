# CLAUDE.md

Project-specific context for Claude Code sessions. The README is the user-facing doc — this file
captures what Claude needs to know that isn't obvious from reading the code.

## What this is

A toolkit that probes a live UE editor's official `ModelContextProtocol` server, captures every
toolset's tools + schemas, and publishes the catalog as a portable Claude skill (one per Epic
release). Replaces blind live `describe_toolset` discovery with file reads (~1,000–3,000× faster).
See README.md "Why this exists" for the full motivation.

## Core invariants — don't break these

1. **Skill folder name == probe filename version.** `skills/ue-official-mcp-X.Y.Z/` matches
   `probes/X.Y.Z.json` exactly. `paths.skill_name()` enforces this; route any new path through
   `paths.py` rather than hardcoding strings.
2. **Both axes use the full `X.Y.Z` version.** Patch releases (`5.8.1`, `5.8.2`) get their own
   probe AND their own skill. Rationale: MCP is Experimental and schemas drift across patches;
   pinning prevents silent breakage when a consumer's editor and the cached schemas disagree.
3. **Generated files are never hand-edited.** Everything under `skills/<X.Y.Z>/references/`
   regenerates from `probes/<X.Y.Z>.json` via `generate.py`. Each generated file has a
   "do not hand-edit" header.
4. **Frontmatter `name:`** in each `SKILL.md` must equal its parent folder name (Anthropic skill
   convention).
5. **`toolset_map.yaml` is the curator source** for domain grouping. Shared across all engine
   versions — one map, many skills. Edit the map, then re-`generate`; never edit the
   `<domain>.md` outputs directly.

## Common commands

All commands run via `uv` (Python deps managed by uv, not pip directly):

- `uv run ue-mcp-skills sync --engine X.Y.Z --launch` — launches UE, probes it, writes
  `probes/X.Y.Z.json` + regenerates the matching skill folder.
- `uv run ue-mcp-skills sync --engine X.Y.Z --endpoint URL` — same, against an already-running
  editor (skips the launch step).
- `uv run ue-mcp-skills generate [--engine X.Y[.Z]]` — offline rebuild from a saved probe.
  With `X.Y`, picks the highest patch present.
- `uv run ue-mcp-skills build [--serve]` — mkdocs site over the engine pinned in `mkdocs.yml`.
- `uv run python -m mkdocs build --strict` — direct mkdocs invocation (what CI runs).

`--engine` defaults to `$UE_MCP_ENGINE_VERSION` → uproject `EngineAssociation` (with patch-zero
padding); `--endpoint` defaults to `$UE_MCP_ENDPOINT` → `http://127.0.0.1:8000/mcp`.

## Architecture pointers

- `scripts/ue_mcp_skills/paths.py` — source of truth for all version-aware paths. Import from here.
- `scripts/ue_mcp_skills/probe.py` — async MCP streamable-HTTP client. Calls `list_toolsets` →
  `describe_toolset` per toolset. Validates each result by checking the response shape (drops
  false positives from prose bullets in the listing).
- `scripts/ue_mcp_skills/generate.py` — pure function of probe JSON + toolset_map. Deterministic
  (stable-sorted) so re-runs from the same probe yield byte-identical output → clean git diffs.
- `scripts/ue_mcp_skills/launch.py` — spawns `UnrealEditor.exe` GUI-windowed, no-focus. Always
  passes `-ModelContextProtocolStartServer -ModelContextProtocolPort=<port-from-endpoint>` because
  the plugin defaults to `bAutoStartServer=false`.
- `scripts/ue_mcp_skills/cli.py` — Typer entry point (`sync`, `generate`, `build`).
- `project/UeMcpProbe.uproject` — Blueprint-only (no `Source/`, no compile),
  `ModelContextProtocol` + `AllToolsets` enabled.

## Behavioral conventions

- **Use `git mv`** for renames so history is preserved. Don't `rm + write`.
- **Don't commit** `.idea/`, `.vscode/`, `site/`, `.venv/`. The `.gitignore` covers them.
- **`describe_toolset` is a recovery mechanism, not a pre-call confirmation.** When operating
  against the actual UE MCP server: call `call_tool` directly from the file's schema; only
  `describe_toolset` to diagnose schema-shaped errors. SKILL.md says this for the consuming
  agent — same rule applies if Claude itself drives the server in a session.
- **MCP port 8000 may be taken** on some hosts by unrelated processes (Manager.exe was a hit
  here once). If `sync --launch` times out, try a different port via
  `--endpoint http://127.0.0.1:8001/mcp`.

## Non-goals — don't add these unless explicitly asked

- Headless UE support (the official MCP server requires the editor running GUI).
- Mocked or synthetic probes (the toolkit is *for* capturing real surfaces; mocks defeat the point).
- Live-probe CI (CI builds from the committed `probes/*.json` only).
- Auto-injecting the generated skill into any host UE project (clean separation).
- Pre-flight `describe_toolset` checks in the published skill (see above).
- Multi-version mkdocs site composition (deferred until UE 5.9 ships; today's `mkdocs.yml`
  pins one engine version).

## End-to-end verification recipe

```bash
uv sync                                                # install deps
uv run ue-mcp-skills sync --engine 5.8.0 --launch       # ~5 min: UE launch + probe + generate
                                                       # expects: 52 toolsets / 830 tools / all mapped
uv run python -m mkdocs build --strict                 # site/ builds clean
uv run ue-mcp-skills generate --engine 5.8.0           # offline path produces identical output
```

## Why hybrid docs (raw + curated + uncategorized)

- **Raw per-toolset files** guarantee completeness regardless of engine version — every probed
  toolset gets a file. Source of truth.
- **Curated domain files** give a scannable routing layer so an agent doesn't read 52 raw files
  to find the right toolset for a task.
- **`uncategorized.md`** is the safety net: a toolset the server reports that isn't in
  `toolset_map.yaml` lands there and `sync` prints a loud `WARNING`. A new Epic toolset surfaces
  noisily instead of vanishing.
