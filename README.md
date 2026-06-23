# ue-official-mcp

A toolkit that **regenerates and publishes reference docs for the official Unreal Engine 5.8
[ModelContextProtocol](https://dev.epicgames.com/documentation) MCP server** by probing a live
editor — and ships them as a portable Claude/agent **skill** plus a browsable
[mkdocs-material](https://squidfunk.github.io/mkdocs-material/) site.

The official UE MCP server is *self-describing* (you call `list_toolsets` / `describe_toolset`
at runtime) but ships **no offline catalog**. With `AllToolsets` enabled it exposes on the order
of **50+ toolsets / 800+ tools**, and the surface drifts between engine versions. This toolkit
captures that surface into version-controlled Markdown you can read, diff, search, and hand to an
agent — without a running editor.

## Why this exists

The official UE MCP server is *self-describing* — agents can already discover everything at runtime
via the three meta-tools (`list_toolsets`, `describe_toolset`, `call_tool`). So why pre-generate a
skill at all?

**1. Discovery cost.** With `AllToolsets`, the server exposes **52 toolsets / 830 tools**. A warm
`describe_toolset` round-trip takes ~300–700 ms on this machine (measured: `PluginToolset` 335 ms,
`SceneTools` 667 ms, `BlueprintTools` 337 ms, `SequencerTools` 335 ms). Reading the equivalent
generated Markdown file is **0.2–0.3 ms** — **1,000–3,000× faster**. Enumerating every toolset to
find the right tool blindly would cost ~20 seconds of editor time per session before any real work.

**2. The MCP server runs on the editor's game thread, serially.** Every `describe_toolset` call
during discovery competes with the actual `call_tool` you want to make. Reading a local file costs
zero editor time. For an agent doing many editor edits per task, this compounds.

**3. Context-window economics.** Streaming `describe_toolset` results into the conversation one
toolset at a time consumes context the agent could spend on the task. The skill gives the agent a
short routing table (`SKILL.md`, ~50 lines) and one focused domain file (the curated tables list
tools without their full JSON schemas, so they stay scannable), and the agent only loads a raw
schema file when it actually needs the schema. Targeted retrieval beats blind enumeration.

**4. Offline planning.** The agent can read this catalog, design a multi-step Blueprint edit, and
write the call sequence **without an editor running** — useful for code review, design discussions,
test scaffolding, and CI. Live `describe_toolset` requires UE booted (a 30–90 s cold start, several
GB of RAM).

**5. Versioned, diff-able surface.** The `ModelContextProtocol` plugin shipped in UE 5.8 and is
flagged Experimental, so toolset/tool surfaces are expected to drift between engine versions. The
committed `probes/<X.Y.Z>.json` files plus the generated Markdown make those changes a normal PR
diff: re-sync against the next engine release and the diff shows exactly what tools were
added/removed/renamed and which schemas changed. A self-describing server alone gives you no such
record.

**6. Routing decisions belong in the skill, not in the model.** Which toolset handles "spawn an
actor"? `SceneTools` or `ActorTools`? Both, with overlapping verbs. The curated `toolset_map.yaml`
+ `SKILL.md` codify those routing choices once, in version control, so every agent session gets the
same answer instead of re-deriving it from tool names.

The trade-off is honest: a generated catalog is a **snapshot**, and schemas can drift between
engine versions. Rather than pay a pre-flight `describe_toolset` on every call, `SKILL.md` tells
the agent to **call directly from the file's schema** and treat `describe_toolset` as the recovery
path — invoked only when a `call_tool` returns a schema-shaped error (missing/unknown field, wrong
type). On the common path (file is still accurate) you pay zero round-trips for confirmation; on
the rare drift path you pay one extra round-trip to diagnose. This bets on the server's error
messages being specific enough to drive the recovery — which they are in the current plugin, but
worth re-checking if Epic changes error formatting.

## What's in here

```
ue-official-mcp/
├─ skills/                            # one folder per engine version — the portable skill artifacts
│  └─ ue-official-mcp-5.8.0/          # drop into .claude/skills/ as-is
│     ├─ SKILL.md                     #   routing layer (frontmatter name: ue-official-mcp-5.8.0)
│     └─ references/                  #   GENERATED — do not hand-edit
│        ├─ index.md                  #     reference hub + live counts/probe stamp
│        ├─ <domain>.md               #     curated domain files (grouped per scripts/toolset_map.yaml)
│        ├─ uncategorized.md          #     safety net for toolsets not yet in the map
│        └─ toolsets/<Name>.md        #     raw per-toolset catalog (full schemas) = source of truth
├─ probes/                            # raw probe dumps — one per Epic release
│  └─ 5.8.0.json
├─ project/                           # empty UE project, MCP enabled — the probe target (version-neutral)
│  └─ UeMcpProbe.uproject              #   plugins: ModelContextProtocol + AllToolsets
├─ scripts/
│  ├─ ue_mcp_skills/                   # python package (probe / generate / launch / cli)
│  └─ toolset_map.yaml                 # toolset -> domain mapping (shared across all engine versions)
└─ mkdocs.yml                         # site build (docs_dir pinned to one skill version)
```

Both probes and skills key on the **full engine version** (`X.Y.Z`). Each Epic release —
including patch releases like `5.8.1`, `5.8.2` — is a distinct probe **and** a distinct skill.
The MCP plugin is Experimental, so schemas can drift across patches; pinning the skill to the
exact version it was probed from makes that explicit and prevents subtle silent breakage when a
consumer's editor and the cached schemas disagree.

When UE 5.8.1 or 5.9.0 lands: `uv run ue-mcp-skills sync --engine <X.Y.Z> --launch` writes
`probes/<X.Y.Z>.json` and `skills/ue-official-mcp-<X.Y.Z>/` next to the existing artifacts.
Tooling stays shared; catalogs are per release.

## Prerequisites

- **Unreal Engine 5.8+** with the `ModelContextProtocol` and `AllToolsets` plugins. The bundled
  `project/UeMcpProbe.uproject` already enables both and is Blueprint-only, so it opens with **no
  compile step**.
- **[uv](https://docs.astral.sh/uv/)** — manages the Python environment (a suitable Python is
  provisioned automatically; no system Python required).

## Quickstart

```bash
# 1. Install dependencies (uv provisions Python + deps)
uv sync

# 2a. Open project/UeMcpProbe.uproject in the matching UE editor (the MCP server starts with it),
#     then probe + regenerate the docs for that engine version:
uv run ue-mcp-skills sync --engine 5.8.0 --endpoint http://127.0.0.1:8000/mcp

# 2b. ...or let the toolkit launch the editor for you (GUI, windowed, no-focus):
uv run ue-mcp-skills sync --engine 5.8.0 --launch

# 3. Build the browsable site (-> ./site), or serve it locally:
uv run ue-mcp-skills build
uv run ue-mcp-skills build --serve
```

> `--engine` accepts `X.Y` or `X.Y.Z` (`5.8` is normalized to `5.8.0`). Defaults to
> `$UE_MCP_ENGINE_VERSION` if set, otherwise `EngineAssociation` from
> `project/UeMcpProbe.uproject` (currently `5.8` → `5.8.0`). For `generate`, passing only `X.Y`
> picks the highest-patch probe present (`probes/X.Y.*.json`) and writes to its matching
> skill folder. The default endpoint is `http://127.0.0.1:8000/mcp` — override with `--endpoint`
> or `$UE_MCP_ENDPOINT`.

## Commands

| Command | What it does |
|---|---|
| `sync` | Probe a running editor (optionally `--launch` it first), write the raw dump to `probes/<X.Y.Z>.json`, then regenerate the matching `skills/ue-official-mcp-<X.Y.Z>/`. |
| `generate` | Regenerate the docs **from a saved probe file only** — no editor needed (offline / CI). |
| `build` | `mkdocs build --strict` over the docs_dir in `mkdocs.yml` into `./site` (`--serve` to preview). |

Key `sync` options: `--engine VERSION` (engine version key, e.g. `5.8`), `--endpoint URL`,
`--launch`, `--engine-path PATH` (UE install dir for `--launch`; or set `UE_ENGINE_PATH`),
`--no-cache` (skip writing the cache).

## How the hybrid docs work

Two layers, generated together so they never disagree:

- **Raw catalog** (`references/toolsets/<Name>.md`) — one file per toolset, verbatim from
  `describe_toolset`: every tool, with full input/output JSON schemas. This is the source of truth
  and is **always complete** regardless of engine version.
- **Curated domain files** (`references/<domain>.md`) — the same toolsets re-grouped into
  human-friendly domains (Blueprint, Material, Niagara, …) per `scripts/toolset_map.yaml`, each
  linking into the raw catalog.

Any toolset the server reports that **isn't** in `toolset_map.yaml` is not dropped — it lands in
`uncategorized.md` and `sync` prints a `WARNING` with the exact mapping line to add. So a
new Epic toolset surfaces loudly instead of silently vanishing.

### Adding a toolset mapping

When `sync` warns about an uncategorized toolset, add it under the right domain in
`scripts/toolset_map.yaml`:

```yaml
domains:
  blueprint:
    title: "Blueprint graphs & logic"
    toolsets:
      - editor_toolset.toolsets.blueprint.BlueprintTools
      - your.new.ToolsetName        # <- add here
```

Re-run `sync` (or `generate`) and the toolset moves into its domain file.

## The skill

Each `skills/ue-official-mcp-<X.Y.Z>/` directory is a self-contained agent skill: drop it into a
project's `.claude/skills/ue-official-mcp-<X.Y.Z>/` and an agent gets the routing layer
(`SKILL.md`) plus the generated reference for that engine version. Multiple versions can coexist —
`.claude/skills/ue-official-mcp-5.8.0/` and `.claude/skills/ue-official-mcp-5.8.1/` are distinct
skills (their frontmatter `name:` differs), so an agent driving one editor pulls in the matching
version and isn't confused by schema drift in the other.

## License

MIT — see [LICENSE](LICENSE).
