"""Allow `python -m ue_mcp_skills` as an alternative to the `ue-mcp-skills` console script."""

from .cli import app

if __name__ == "__main__":
    app()
