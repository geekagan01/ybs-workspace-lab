import platform
from pathlib import Path
from typing import Annotated

import typer

from ybs_cli import __version__
from ybs_cli.errors import YbsError
from ybs_cli.root import find_workspace_root

app = typer.Typer(help="Repository-first AI development orchestration")


def _show_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def callback(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_show_version,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Repository-first AI development orchestration."""


def _exit_for_error(error: YbsError) -> None:
    typer.echo(error.message, err=True)
    raise typer.Exit(code=error.code)


@app.command()
def doctor() -> None:
    """Report the active Python version and workspace root."""
    try:
        root = find_workspace_root(Path.cwd())
    except YbsError as error:
        _exit_for_error(error)
    typer.echo(f"Python: {platform.python_version()}")
    typer.echo(f"Root: {root}")


def main() -> None:
    app()
