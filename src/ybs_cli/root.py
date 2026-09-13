from pathlib import Path

from ybs_cli.errors import YbsError


def find_workspace_root(start: Path) -> Path:
    """Return the nearest ancestor marked as a YBS workspace."""
    current = start.resolve()
    while True:
        manifest = current / "pyproject.toml"
        if manifest.is_file():
            text = manifest.read_text()
            if "[tool.ybs]" in text and "workspace = true" in text:
                return current
        if current.parent == current:
            raise YbsError("YBS workspace root not found", 5)
        current = current.parent
