"""Repo-relative paths. The package is run from a clone (not pip-installed), so all
artifacts resolve relative to the repository root."""

from __future__ import annotations

from pathlib import Path

# scripts/ue_mcp_skills/paths.py  ->  parents[2] is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]

SKILL_DIR = REPO_ROOT / "skill"
REFERENCES_DIR = SKILL_DIR / "references"
TOOLSETS_DIR = REFERENCES_DIR / "toolsets"

CACHE_PATH = REPO_ROOT / "cache" / "probe.json"
TOOLSET_MAP_PATH = REPO_ROOT / "scripts" / "toolset_map.yaml"
PROJECT_UPROJECT = REPO_ROOT / "project" / "UeMcpProbe.uproject"
SITE_DIR = REPO_ROOT / "site"

DEFAULT_ENDPOINT = "http://127.0.0.1:8000/mcp"
