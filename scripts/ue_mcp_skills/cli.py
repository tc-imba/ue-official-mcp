"""`ue-mcp-skills` command-line interface."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional

import typer

from . import generate as generate_mod
from . import launch as launch_mod
from . import paths
from . import probe as probe_mod

app = typer.Typer(
    add_completion=False,
    help="Regenerate and build the official UE MCP reference docs (per engine version).",
)


def _print_summary(summary: dict) -> None:
    typer.echo(
        f"  engine: UE {summary['engine_version']}   "
        f"toolsets: {summary['toolset_count']}   "
        f"tools: {summary['tool_count']}   domains: {summary['domain_count']}"
    )
    skipped = summary.get("skipped_candidates") or []
    if skipped:
        typer.echo(
            f"  note: {len(skipped)} listing candidate(s) were not valid toolsets and were skipped."
        )
    unmapped = summary.get("unmapped") or []
    if unmapped:
        typer.secho(
            "  WARNING: toolsets not in scripts/toolset_map.yaml "
            "(routed to uncategorized.md):",
            fg="yellow",
        )
        for name in unmapped:
            typer.secho(f"    - {name}", fg="yellow")
        typer.secho(
            "  Add each under the right domain in scripts/toolset_map.yaml and re-run.",
            fg="yellow",
        )
    else:
        typer.echo("  all toolsets mapped to a domain.")


def _resolve_engine(engine_version: Optional[str]) -> str:
    """Resolve --engine | $UE_MCP_ENGINE_VERSION | uproject EngineAssociation, normalized to X.Y.Z."""
    raw = engine_version or os.environ.get("UE_MCP_ENGINE_VERSION")
    if raw:
        return paths.normalize_engine_version(raw)
    return paths.default_engine_version()


@app.command()
def sync(
    engine_version: Optional[str] = typer.Option(
        None, "--engine", help="UE engine version key, e.g. '5.8'. "
        "Default: $UE_MCP_ENGINE_VERSION or EngineAssociation in project/UeMcpProbe.uproject."
    ),
    endpoint: Optional[str] = typer.Option(
        None, help="MCP endpoint URL. Default: $UE_MCP_ENDPOINT or http://127.0.0.1:8000/mcp"
    ),
    launch: bool = typer.Option(
        False, help="Launch the bundled UE project (GUI, no-focus) before probing."
    ),
    engine_path: Optional[str] = typer.Option(
        None, "--engine-path",
        help="UE install dir or UnrealEditor.exe (for --launch). "
        "Else $UE_ENGINE_PATH / Windows registry / default path.",
    ),
    timeout: float = typer.Option(
        180.0, help="Seconds to wait for the endpoint when --launch is used."
    ),
    no_cache: bool = typer.Option(False, help="Do not write the cache file."),
) -> None:
    """Probe a running editor and regenerate the reference docs for one engine version."""
    ev = _resolve_engine(engine_version)
    target = endpoint or os.environ.get("UE_MCP_ENDPOINT") or paths.DEFAULT_ENDPOINT
    probe_path = paths.probe_path(ev)

    if launch:
        typer.echo(f"Launching editor for {paths.PROJECT_UPROJECT.name} (engine UE {ev}) ...")
        launch_mod.launch_editor(paths.PROJECT_UPROJECT, ev, engine_path, target)
        typer.echo(f"Waiting up to {timeout:.0f}s for {target} ...")
        launch_mod.wait_for_endpoint(target, timeout)

    typer.echo(f"Probing {target} (engine UE {ev}) ...")
    data = probe_mod.probe(target)
    data["probed_at"] = datetime.now(timezone.utc).isoformat()
    data["engine_version"] = ev

    if not no_cache:
        probe_path.parent.mkdir(parents=True, exist_ok=True)
        probe_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        typer.echo(f"Wrote {probe_path.relative_to(paths.REPO_ROOT)}")

    summary = generate_mod.regenerate_from_data(data, paths.TOOLSET_MAP_PATH, ev)
    typer.echo("Generated reference docs:")
    _print_summary(summary)


@app.command()
def generate(
    engine_version: Optional[str] = typer.Option(
        None, "--engine", help="UE engine version, 'X.Y' or 'X.Y.Z' (e.g. '5.8' or '5.8.0'). "
        "X.Y resolves to the highest-patch probe file present. "
        "Default: $UE_MCP_ENGINE_VERSION or EngineAssociation in project/UeMcpProbe.uproject."
    ),
) -> None:
    """Regenerate docs from a saved probe file (no editor required)."""
    raw = engine_version or os.environ.get("UE_MCP_ENGINE_VERSION")

    if raw and len(raw.split(".")) == 2:
        # User passed X.Y — pick the highest patch present in probes/.
        latest = paths.latest_probe_for(raw)
        if latest is None:
            typer.secho(f"No probe matching {raw}.*.json in {paths.PROBES_DIR}.", fg="red")
            raise typer.Exit(1)
        ev = latest.stem  # X.Y.Z
        probe_path = latest
    else:
        ev = _resolve_engine(engine_version)
        probe_path = paths.probe_path(ev)
        if not probe_path.exists():
            typer.secho(f"No probe at {probe_path}. Run `sync --engine {ev}` first.", fg="red")
            raise typer.Exit(1)

    summary = generate_mod.regenerate_from_probe(probe_path, paths.TOOLSET_MAP_PATH, ev)
    typer.echo(f"Regenerated reference docs from {probe_path.relative_to(paths.REPO_ROOT)}:")
    _print_summary(summary)


@app.command()
def build(
    serve: bool = typer.Option(False, help="Run `mkdocs serve` instead of building."),
    strict: bool = typer.Option(True, help="Pass --strict to `mkdocs build`."),
) -> None:
    """Build (or serve) the mkdocs-material site for the currently configured docs_dir."""
    cmd = [sys.executable, "-m", "mkdocs", "serve" if serve else "build"]
    if not serve and strict:
        cmd.append("--strict")
    result = subprocess.run(cmd, cwd=str(paths.REPO_ROOT))
    raise typer.Exit(result.returncode)


if __name__ == "__main__":
    app()
