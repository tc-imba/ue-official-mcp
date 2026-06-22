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
    help="Regenerate and build the official UE 5.8 MCP reference docs.",
)


def _print_summary(summary: dict) -> None:
    typer.echo(
        f"  toolsets: {summary['toolset_count']}   "
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
            "(routed to official-uncategorized.md):",
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


@app.command()
def sync(
    endpoint: Optional[str] = typer.Option(
        None, help="MCP endpoint URL. Default: $UE_MCP_ENDPOINT or http://127.0.0.1:8000/mcp"
    ),
    launch: bool = typer.Option(
        False, help="Launch the bundled UE project (GUI, no-focus) before probing."
    ),
    engine: Optional[str] = typer.Option(
        None,
        help="UE install dir or UnrealEditor.exe (for --launch). "
        "Else $UE_ENGINE_PATH / Windows registry / default path.",
    ),
    timeout: float = typer.Option(
        180.0, help="Seconds to wait for the endpoint when --launch is used."
    ),
    no_cache: bool = typer.Option(False, help="Do not write cache/probe.json."),
) -> None:
    """Probe a running editor and regenerate the reference docs."""
    target = endpoint or os.environ.get("UE_MCP_ENDPOINT") or paths.DEFAULT_ENDPOINT

    if launch:
        typer.echo(f"Launching editor for {paths.PROJECT_UPROJECT.name} ...")
        launch_mod.launch_editor(paths.PROJECT_UPROJECT, engine)
        typer.echo(f"Waiting up to {timeout:.0f}s for {target} ...")
        launch_mod.wait_for_endpoint(target, timeout)

    typer.echo(f"Probing {target} ...")
    data = probe_mod.probe(target)
    data["probed_at"] = datetime.now(timezone.utc).isoformat()

    if not no_cache:
        paths.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        paths.CACHE_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        typer.echo(f"Wrote {paths.CACHE_PATH.relative_to(paths.REPO_ROOT)}")

    summary = generate_mod.regenerate_from_data(data, paths.TOOLSET_MAP_PATH)
    typer.echo("Generated reference docs:")
    _print_summary(summary)


@app.command()
def generate() -> None:
    """Regenerate docs from cache/probe.json only (no editor required)."""
    if not paths.CACHE_PATH.exists():
        typer.secho(f"No cache at {paths.CACHE_PATH}. Run `sync` first.", fg="red")
        raise typer.Exit(1)
    summary = generate_mod.regenerate_from_cache(paths.CACHE_PATH, paths.TOOLSET_MAP_PATH)
    typer.echo("Regenerated reference docs from cache:")
    _print_summary(summary)


@app.command()
def build(
    serve: bool = typer.Option(False, help="Run `mkdocs serve` instead of building."),
    strict: bool = typer.Option(True, help="Pass --strict to `mkdocs build`."),
) -> None:
    """Build (or serve) the mkdocs-material site."""
    cmd = [sys.executable, "-m", "mkdocs", "serve" if serve else "build"]
    if not serve and strict:
        cmd.append("--strict")
    result = subprocess.run(cmd, cwd=str(paths.REPO_ROOT))
    raise typer.Exit(result.returncode)


if __name__ == "__main__":
    app()
