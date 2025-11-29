"""Board (widget) commands."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from favro_cli.api.client import FavroAPIError, FavroAuthError, FavroClient
from favro_cli.api.models import Card, Column
from favro_cli.config import get_credentials, get_organization_id
from favro_cli.output.formatters import (
    output_error,
    output_json,
    output_panel,
    output_table,
)
from favro_cli.state import state


app = typer.Typer(help="Board commands")
console = Console()


def get_client() -> FavroClient:
    """Get an authenticated client with organization."""
    creds = get_credentials()
    if creds is None:
        output_error("Not logged in. Run 'favro login' first.")
        raise typer.Exit(1)

    org_id = get_organization_id()
    if org_id is None:
        output_error("No organization selected. Run 'favro org select <id>' first.")
        raise typer.Exit(1)

    email, token = creds
    return FavroClient(email, token, org_id)


@app.command("list")
def list_boards(
    collection_id: Annotated[
        str | None,
        typer.Option("--collection", "-c", help="Filter by collection ID"),
    ] = None,
    archived: Annotated[
        bool,
        typer.Option("--archived", "-a", help="Include archived boards"),
    ] = False,
) -> None:
    """List all boards in the organization."""
    try:
        with get_client() as client:
            widgets = client.get_widgets(collection_id=collection_id, archived=archived)

            # Filter to only show boards (not backlogs)
            boards = [w for w in widgets if w.type == "board"]

            if state["json"]:
                output_json(boards)
            else:
                output_table(
                    boards,
                    [
                        ("widget_common_id", "ID"),
                        ("name", "Name"),
                        ("color", "Color"),
                        ("type", "Type"),
                    ],
                    title="Boards",
                )
    except FavroAuthError:
        output_error("Invalid credentials. Please login again.")
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def show(
    board_id: Annotated[
        str,
        typer.Argument(help="Board ID (widgetCommonId)"),
    ],
) -> None:
    """Show board details with columns and card counts."""
    try:
        with get_client() as client:
            widget = client.get_widget(board_id)
            columns = client.get_columns(board_id)

            if state["json"]:
                output_json({
                    "board": widget.model_dump(by_alias=True),
                    "columns": [c.model_dump(by_alias=True) for c in columns],
                })
            else:
                # Show board info
                output_panel(
                    widget,
                    [
                        ("widget_common_id", "ID"),
                        ("name", "Name"),
                        ("type", "Type"),
                        ("color", "Color"),
                    ],
                    title=f"Board: {widget.name}",
                )

                # Show columns
                console.print()
                output_table(
                    columns,
                    [
                        ("column_id", "Column ID"),
                        ("name", "Name"),
                        ("card_count", "Cards"),
                        ("position", "Position"),
                    ],
                    title="Columns",
                )
    except FavroAuthError:
        output_error("Invalid credentials. Please login again.")
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def view(
    board_id: Annotated[
        str,
        typer.Argument(help="Board ID (widgetCommonId)"),
    ],
    max_cards: Annotated[
        int,
        typer.Option("--max-cards", "-m", help="Max cards to show per column"),
    ] = 5,
) -> None:
    """View board with cards in a Kanban-style layout."""
    try:
        with get_client() as client:
            widget = client.get_widget(board_id)
            columns = client.get_columns(board_id)
            cards = client.get_cards(widget_common_id=board_id)

            if state["json"]:
                output_json({
                    "board": widget.model_dump(by_alias=True),
                    "columns": [c.model_dump(by_alias=True) for c in columns],
                    "cards": [c.model_dump(by_alias=True) for c in cards],
                })
            else:
                _render_board_view(widget.name, columns, cards, max_cards)

    except FavroAuthError:
        output_error("Invalid credentials. Please login again.")
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


def _render_board_view(
    board_name: str,
    columns: list[Column],
    cards: list[Card],
    max_cards: int,
) -> None:
    """Render a Kanban-style board view."""
    # Sort columns by position
    sorted_columns = sorted(columns, key=lambda c: c.position)

    # Group cards by column
    cards_by_column: dict[str, list[Card]] = {}
    for card in cards:
        if card.column_id:
            if card.column_id not in cards_by_column:
                cards_by_column[card.column_id] = []
            cards_by_column[card.column_id].append(card)

    # Sort cards by position within each column
    for col_id in cards_by_column:
        cards_by_column[col_id].sort(
            key=lambda c: c.list_position if c.list_position is not None else 0
        )

    # Create table
    table = Table(title=f"Board: {board_name}", show_lines=True)

    # Add column headers
    for col in sorted_columns:
        card_count = len(cards_by_column.get(col.column_id, []))
        table.add_column(f"{col.name} ({card_count})", width=25)

    # Determine max rows needed
    max_rows = max(
        min(len(cards_by_column.get(col.column_id, [])), max_cards)
        for col in sorted_columns
    ) if sorted_columns else 0

    # Add rows
    for row_idx in range(max_rows):
        row_cells: list[str] = []
        for col in sorted_columns:
            col_cards = cards_by_column.get(col.column_id, [])
            if row_idx < len(col_cards):
                card = col_cards[row_idx]
                card_text = _format_card_cell(card)
                row_cells.append(card_text)
            else:
                row_cells.append("")
        table.add_row(*row_cells)

    # Add "..." row if there are more cards
    has_more = False
    more_row: list[str] = []
    for col in sorted_columns:
        col_cards = cards_by_column.get(col.column_id, [])
        remaining = len(col_cards) - max_cards
        if remaining > 0:
            has_more = True
            more_row.append(f"[dim]... +{remaining} more[/dim]")
        else:
            more_row.append("")

    if has_more:
        table.add_row(*more_row)

    console.print(table)


def _format_card_cell(card: Card) -> str:
    """Format a card for display in a table cell."""
    lines: list[str] = []

    # Card identifier and name
    lines.append(f"[bold][#{card.sequential_id}][/bold] {card.name[:20]}")

    # Truncate name if too long
    if len(card.name) > 20:
        lines[0] = f"[bold][#{card.sequential_id}][/bold] {card.name[:17]}..."

    # Show due date if set
    if card.due_date:
        due_str = card.due_date.strftime("%Y-%m-%d")
        lines.append(f"[dim]Due: {due_str}[/dim]")

    # Show assignee count if any
    if card.assignments:
        lines.append(f"[dim]{len(card.assignments)} assigned[/dim]")

    # Show task progress if any
    if card.tasks_total > 0:
        lines.append(f"[dim]Tasks: {card.tasks_done}/{card.tasks_total}[/dim]")

    return "\n".join(lines)
