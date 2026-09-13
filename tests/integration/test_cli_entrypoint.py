import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]


def run_ybs(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "ybs", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_help_and_version_are_available() -> None:
    help_result = run_ybs("--help")
    version_result = run_ybs("--version")

    assert help_result.returncode == 0
    assert "Repository-first AI development orchestration" in help_result.stdout
    assert version_result.returncode == 0
    assert "0.1.0" in version_result.stdout


def test_find_workspace_root_from_nested_directory(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    nested = root / "docs" / "notes"
    nested.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[tool.ybs]\nworkspace = true\n")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; from ybs_cli.root import find_workspace_root; "
            "print(find_workspace_root(Path.cwd()))",
        ],
        cwd=nested,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == str(root)
