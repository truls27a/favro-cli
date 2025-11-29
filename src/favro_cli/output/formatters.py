"""Output formatters for CLI output."""

import json
from typing import Any, Sequence

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


def output_json(data: BaseModel | Sequence[BaseModel] | dict[str, Any]) -> None:
    """Output data as JSON."""
    if isinstance(data, BaseModel):
        json_data = data.model_dump(by_alias=True)
    elif isinstance(data, dict):
        json_data = data
    else:
        # It's a sequence
        json_data = [item.model_dump(by_alias=True) for item in data]
    # Use print() instead of console.print() to avoid Rich word-wrapping
    print(json.dumps(json_data, indent=2, default=str))


def output_table(
    data: Sequence[BaseModel],
    columns: list[tuple[str, str]],
    title: str | None = None,
) -> None:
    """Output data as a Rich table.

    Args:
        data: List of Pydantic models to display
        columns: List of (attribute_name, column_header) tuples
        title: Optional table title
    """
    table = Table(title=title)

    for _, header in columns:
        table.add_column(header)

    for item in data:
        row: list[str] = []
        for attr, _ in columns:
            value = getattr(item, attr, "")
            if value is None:
                value = ""
            row.append(str(value))
        table.add_row(*row)

    console.print(table)


def output_panel(
    data: BaseModel,
    fields: list[tuple[str, str]],
    title: str,
) -> None:
    """Output a single item as a Rich panel.

    Args:
        data: Pydantic model to display
        fields: List of (attribute_name, display_label) tuples
        title: Panel title
    """
    lines: list[str] = []
    for attr, label in fields:
        value = getattr(data, attr, None)
        if value is not None:
            lines.append(f"[bold]{label}:[/bold] {value}")

    content = "\n".join(lines)
    panel = Panel(content, title=title)
    console.print(panel)


def output_error(message: str) -> None:
    """Output an error message."""
    error_console.print(f"[red]Error:[/red] {message}")


def output_success(message: str) -> None:
    """Output a success message."""
    console.print(f"[green]{message}[/green]")


def output_warning(message: str) -> None:
    """Output a warning message."""
    console.print(f"[yellow]{message}[/yellow]")


def output_info(message: str) -> None:
    """Output an info message."""
    console.print(message)
