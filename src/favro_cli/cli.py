"""Main CLI application."""

from typing import Annotated, Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="favro",
    help="CLI for Favro project management",
    no_args_is_help=True,
)

console = Console()

# Global state for JSON output mode
state: dict[str, bool] = {"json": False}


def version_callback(value: bool) -> None:
    if value:
        from favro_cli import __version__

        console.print(f"favro-cli version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Output in JSON format.",
        ),
    ] = False,
) -> None:
    """Favro CLI - Manage your Favro boards from the command line."""
    state["json"] = json_output
