---
name: ue-official-mcp
description: Use when driving a running Unreal Editor over the official UE 5.8 MCP server — to pick the correct toolset and tool for an editor-automation task (spawn/edit actors, Blueprints, materials, Niagara, animation/Sequencer, meshes, GAS, UMG, StateTree, data tables, run automation tests, inspect Slate, etc.). Routes a task to the matching per-domain tool reference under references/ and explains how to call via the Tool Search meta-tools.
---

# ue-official-mcp — pick the right official UE MCP tool

Operational routing for the **official UE 5.8 MCP** server (the `ModelContextProtocol` plugin). This
skill is the decision layer + an index into the generated tool catalog under `references/`.

With `AllToolsets` enabled, the server exposes **dozens of toolsets / hundreds of tools** over HTTP
(streamable, default `http://127.0.0.1:8000/mcp`). It requires the editor running and runs
**serially on the game thread** — never issue overlapping calls. For the exact live counts and the
snapshot date this reference was generated from, see [`references/index.md`](references/index.md).

## When to use
Before any official-MCP editor-automation call — to choose **which toolset/tool** fits the task,
then read the matching `references/official-*.md` for tool names, then confirm the exact schema
against the live server before writing arguments.

## How to call
Tool Search is on, so `tools/list` shows only 3 meta-tools. In a Claude Code session they surface as
**`mcp__<server-key>__*`**, where `<server-key>` is the name given to the server in the MCP client's
`.mcp.json` (Epic's setup example uses `unreal-mcp` → `mcp__unreal-mcp__*`). The three meta-tools:
1. `list_toolsets` — names + summaries of the enabled toolsets.
2. `describe_toolset(toolset_name)` — the tools (names + schemas) in one toolset.
3. `call_tool(name, arguments)` — dispatch a tool; result returns on the same turn.

Flow: identify the domain below → open its `references/official-*.md` for the toolset + tool name →
**`describe_toolset` to confirm the current parameter names** → `call_tool`. The references are a
generated snapshot; param names can drift between engine versions, so confirm before relying on them.

## Routing — task domain → reference
| Task domain | Reference |
|---|---|
| Blueprint graphs & logic (incl. graph DSL) | [`references/official-blueprint.md`](references/official-blueprint.md) |
| Materials, material instances, textures | [`references/official-material.md`](references/official-material.md) |
| Niagara (system/emitter/module/component) | [`references/official-niagara.md`](references/official-niagara.md) |
| Animation, Control Rig, Sequencer | [`references/official-animation-sequencer.md`](references/official-animation-sequencer.md) |
| Static/skeletal mesh, primitives, PCG | [`references/official-mesh-geometry.md`](references/official-mesh-geometry.md) |
| Scene/level, actors, assets, objects | [`references/official-scene-actor.md`](references/official-scene-actor.md) |
| GAS (cues, attribute sets, ASC inspect), GameplayTags | [`references/official-gas.md`](references/official-gas.md) |
| UMG, StateTree, BehaviorTree, WorldConditions, Conversation | [`references/official-ui-state.md`](references/official-ui-state.md) |
| Data/Curve/String tables, Data assets, DataRegistry | [`references/official-data-tables.md`](references/official-data-tables.md) |
| Editor control (console/PIE/viewport), logs, automation tests, Slate inspect | [`references/official-editor-automation.md`](references/official-editor-automation.md) |
| GameFeatures, Plugins, Dataflow, Physics, SemanticSearch, AgentSkill | [`references/official-project-misc.md`](references/official-project-misc.md) |

Each domain file links into the **raw per-toolset catalog** ([`references/toolsets/`](references/toolsets/index.md)),
which carries every tool's full input/output JSON schema verbatim from `describe_toolset`.

## Gotchas
- **Experimental** — APIs/data formats may change; re-`describe_toolset` if a call's schema looks off.
- **Editor must be running**; calls are serial — one at a time.
- **`AgentSkillToolset.CreateSkill`/`UpdateSkill` require explicit user permission** (the tools say so)
  — don't author AgentSkills unprompted.
- **Regenerating this reference**: run `uv run ue-mcp-skills sync` (probes a live editor and rewrites
  everything under `references/`). The generated files carry a stamp header — do not hand-edit them;
  edit the domain grouping in `scripts/toolset_map.yaml` instead.
