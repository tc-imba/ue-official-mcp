"""Repo-relative paths.

Two version-axes:

- Probe files key on the **full** engine version (`X.Y.Z`, e.g. `5.8.0`): one probe file
  per Epic release in the `probes/` directory. Re-probing UE 5.8.1 writes a new file
  alongside the 5.8.0 one; git history preserves the patch-level drift.
- Skill folders key on the **major.minor** (`X.Y`, e.g. `5.8`): one skill per minor line
  under `skills/ue-official-mcp-X.Y/`. Patch-level re-syncs overwrite the same folder so
  consumers don't have to reinstall the skill for every Epic hotfix.

`normalize_engine_version` accepts both forms — `"5.8"` is treated as `"5.8.0"`.
"""

from __future__ import annotations

import json
from pathlib import Path

# scripts/ue_mcp_skills/paths.py  ->  parents[2] is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]

# Version-neutral paths.
PROJECT_DIR = REPO_ROOT / "project"
PROJECT_UPROJECT = PROJECT_DIR / "UeMcpProbe.uproject"
TOOLSET_MAP_PATH = REPO_ROOT / "scripts" / "toolset_map.yaml"
SKILLS_DIR = REPO_ROOT / "skills"
PROBES_DIR = REPO_ROOT / "probes"
SITE_DIR = REPO_ROOT / "site"

DEFAULT_ENDPOINT = "http://127.0.0.1:8000/mcp"


def normalize_engine_version(version: str) -> str:
    """Accept `X.Y` or `X.Y.Z`; return canonical `X.Y.Z` (pads `.0` for X.Y)."""
    parts = version.split(".")
    if len(parts) == 2:
        return f"{version}.0"
    if len(parts) == 3:
        return version
    raise ValueError(
        f"Engine version must be 'X.Y' or 'X.Y.Z' (got {version!r})."
    )


def major_minor(version: str) -> str:
    """`5.8.0` -> `5.8`. Also fine for already-major.minor input."""
    return ".".join(normalize_engine_version(version).split(".")[:2])


def skill_name(version: str) -> str:
    """Skill folder + frontmatter `name:` for a given engine line, e.g. 'ue-official-mcp-5.8'."""
    return f"ue-official-mcp-{major_minor(version)}"


def skill_dir(version: str) -> Path:
    return SKILLS_DIR / skill_name(version)


def references_dir(version: str) -> Path:
    return skill_dir(version) / "references"


def toolsets_dir(version: str) -> Path:
    return references_dir(version) / "toolsets"


def probe_path(version: str) -> Path:
    """One probe file per full engine version, e.g. `probes/5.8.0.json`."""
    return PROBES_DIR / f"{normalize_engine_version(version)}.json"


def latest_probe_for(major_minor_version: str) -> Path | None:
    """Highest-patch probe file for a given major.minor, or None if none exist."""
    mm = major_minor(major_minor_version)
    candidates = sorted(
        PROBES_DIR.glob(f"{mm}.*.json"),
        key=lambda p: tuple(int(x) for x in p.stem.split(".")),
    )
    return candidates[-1] if candidates else None


def default_engine_version() -> str:
    """Read EngineAssociation from the bundled probe uproject, normalized to X.Y.Z."""
    data = json.loads(PROJECT_UPROJECT.read_text(encoding="utf-8"))
    value = data.get("EngineAssociation") or ""
    if not value:
        raise RuntimeError(
            f"EngineAssociation missing from {PROJECT_UPROJECT}; pass --engine explicitly."
        )
    return normalize_engine_version(value)
