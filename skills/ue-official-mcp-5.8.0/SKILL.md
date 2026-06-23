---
name: ue-official-mcp-5.8.0
description: Use when driving a running Unreal Engine 5.8.0 editor over the official UE MCP server — to pick the correct toolset and tool for an editor-automation task (spawn/edit actors, Blueprints, materials, Niagara, animation/Sequencer, meshes, GAS, UMG, StateTree, data tables, run automation tests, inspect Slate, etc.). Routes a task to the matching per-domain tool reference under references/ and explains how to call via the Tool Search meta-tools. Schemas are pinned to UE 5.8.0; use the matching `ue-official-mcp-<X.Y.Z>` skill for other engine versions.
---

# ue-official-mcp-5.8.0 — pick the right UE 5.8.0 MCP tool

Operational routing for the **official Unreal Engine 5.8.0 MCP** server (the `ModelContextProtocol`
plugin). This skill is the decision layer + an index into the generated tool catalog under
`references/`. **All schemas in this skill are captured from UE 5.8.0** — for other engine versions
(including UE 5.8 patch releases) use the matching `ue-official-mcp-<X.Y.Z>` skill, since the MCP
plugin is Experimental and surfaces drift between releases.

With `AllToolsets` enabled, the server exposes **dozens of toolsets / hundreds of tools** over HTTP
(streamable, default `http://127.0.0.1:8000/mcp`). It requires the editor running and runs
**serially on the game thread** — never issue overlapping calls. For the exact live counts and the
snapshot date this reference was generated from, see [`references/index.md`](references/index.md).

## When to use
Before any official-MCP editor-automation call — to choose **which toolset/tool** fits the task,
then read the matching `references/*.md` for tool names and (in the raw per-toolset file under
`references/toolsets/`) the full input/output JSON schemas. Call directly from those schemas —
no `describe_toolset` pre-flight needed.

## How to call
Tool Search is on, so `tools/list` shows only 3 meta-tools. In a Claude Code session they surface as
**`mcp__<server-key>__*`**, where `<server-key>` is the name given to the server in the MCP client's
`.mcp.json` (Epic's setup example uses `unreal-mcp` → `mcp__unreal-mcp__*`). The three meta-tools:
1. `list_toolsets` — names + summaries of the enabled toolsets. **Don't call** for discovery: use
   the routing table below.
2. `describe_toolset(toolset_name)` — the tools (names + schemas) in one toolset. **Only call** as
   the recovery path when a `call_tool` returns a schema-shaped error (missing/unknown field, wrong
   type), to check whether the live schema has drifted from the file.
3. `call_tool(name, arguments)` — dispatch a tool; result returns on the same turn.

Flow: identify the domain below → open its `references/*.md` for the toolset + tool name → open the
raw `references/toolsets/<Name>.md` for the full input schema → `call_tool` directly. If the call
returns a schema-shaped error, re-`describe_toolset` to identify drift, then retry — and consider
flagging the drift so a maintainer can re-`sync`.

## Routing — task domain → reference
| Task domain | Reference |
|---|---|
| Blueprint graphs & logic (incl. graph DSL) | [`references/blueprint.md`](references/blueprint.md) |
| Materials, material instances, textures | [`references/material.md`](references/material.md) |
| Niagara (system/emitter/module/component) | [`references/niagara.md`](references/niagara.md) |
| Animation, Control Rig, Sequencer | [`references/animation-sequencer.md`](references/animation-sequencer.md) |
| Static/skeletal mesh, primitives, PCG | [`references/mesh-geometry.md`](references/mesh-geometry.md) |
| Scene/level, actors, assets, objects | [`references/scene-actor.md`](references/scene-actor.md) |
| GAS (cues, attribute sets, ASC inspect), GameplayTags | [`references/gas.md`](references/gas.md) |
| UMG, StateTree, BehaviorTree, WorldConditions, Conversation | [`references/ui-state.md`](references/ui-state.md) |
| Data/Curve/String tables, Data assets, DataRegistry | [`references/data-tables.md`](references/data-tables.md) |
| Editor control (console/PIE/viewport), logs, automation tests, Slate inspect | [`references/editor-automation.md`](references/editor-automation.md) |
| GameFeatures, Plugins, Dataflow, Physics, SemanticSearch, AgentSkill | [`references/project-misc.md`](references/project-misc.md) |

Each domain file links into the **raw per-toolset catalog** ([`references/toolsets/`](references/toolsets/index.md)),
which carries every tool's full input/output JSON schema verbatim from `describe_toolset`.

## Gotchas
- **Experimental** — APIs/data formats may change between engine versions. The reference is a
  snapshot from when `sync` last ran (see `references/index.md` for the date). Trust the schema
  optimistically; recover via `describe_toolset` only if a `call_tool` returns a schema-shaped error.
- **Editor must be running**; calls are serial — one at a time.
- **`AgentSkillToolset.CreateSkill`/`UpdateSkill` require explicit user permission** (the tools say so)
  — don't author AgentSkills unprompted.
- **Regenerating this reference**: run `uv run ue-mcp-skills sync` (probes a live editor and rewrites
  everything under `references/`). The generated files carry a stamp header — do not hand-edit them;
  edit the domain grouping in `scripts/toolset_map.yaml` instead.
