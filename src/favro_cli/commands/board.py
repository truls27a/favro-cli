"""Board (widget) commands."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from favro_cli.api.client import FavroAPIError, FavroAuthError
from favro_cli.api.models import Card, Column, Tag
from favro_cli.commands.common import get_client
from favro_cli.config import get_board_id, set_board_id
from favro_cli.output.formatters import (
    output_error,
    output_json,
    output_panel,
    output_success,
    output_table,
)
from favro_cli.resolvers import BoardResolver, ResolverError

app = typer.Typer(
    help="Board commands",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


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
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output in JSON format"),
    ] = False,
) -> None:
    """List all boards in the organization."""
    try:
        with get_client() as client:
            widgets = client.get_widgets(collection_id=collection_id, archived=archived)

            # Filter to only show boards (not backlogs)
            boards = [w for w in widgets if w.type == "board"]

            if json_output:
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
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def show(
    board_id: Annotated[
        str | None,
        typer.Argument(help="Board ID or name (uses default if not specified)"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output in JSON format"),
    ] = False,
) -> None:
    """Show board details with columns and card counts."""
    # Use default board if not specified
    effective_board_id = board_id or get_board_id()

    if not effective_board_id:
        output_error(
            "No board specified and no default set. Run 'favro board select <id>' first."
        )
        raise typer.Exit(1)

    try:
        with get_client() as client:
            resolver = BoardResolver(client)
            widget = resolver.resolve(effective_board_id)
            columns = client.get_columns(widget.widget_common_id)
            columns = sorted(columns, key=lambda c: c.position)

            if json_output:
                output_json(
                    {
                        "board": widget.model_dump(by_alias=True),
                        "columns": [c.model_dump(by_alias=True) for c in columns],
                    }
                )
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
    except ResolverError as e:
        output_error(str(e))
        raise typer.Exit(1)
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def view(
    board_id: Annotated[
        str | None,
        typer.Argument(help="Board ID or name (uses default if not specified)"),
    ] = None,
    max_cards: Annotated[
        int,
        typer.Option("--max-cards", "-m", help="Max cards to show per column"),
    ] = 7,
    show_all: Annotated[
        bool,
        typer.Option("--all", "-a", help="Show all cards (no limit)"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output in JSON format"),
    ] = False,
) -> None:
    """View board with cards in a Kanban-style layout."""
    # Use default board if not specified
    effective_board_id = board_id or get_board_id()

    if not effective_board_id:
        output_error(
            "No board specified and no default set. Run 'favro board select <id>' first."
        )
        raise typer.Exit(1)

    if show_all:
        max_cards = 10000
    try:
        with get_client() as client:
            resolver = BoardResolver(client)
            widget = resolver.resolve(effective_board_id)
            columns = client.get_columns(widget.widget_common_id)
            cards = client.get_cards(widget_common_id=widget.widget_common_id)
            tags = client.get_tags()
            tags_map = {t.tag_id: t for t in tags}

            if json_output:
                output_json(
                    {
                        "board": widget.model_dump(by_alias=True),
                        "columns": [c.model_dump(by_alias=True) for c in columns],
                        "cards": [c.model_dump(by_alias=True) for c in cards],
                    }
                )
            else:
                _render_board_view(widget.name, columns, cards, max_cards, tags_map)

    except ResolverError as e:
        output_error(str(e))
        raise typer.Exit(1)
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def select(
    board_id: Annotated[
        str,
        typer.Argument(help="Board ID or name"),
    ],
) -> None:
    """Select a board as default."""
    try:
        with get_client() as client:
            resolver = BoardResolver(client)
            board = resolver.resolve(board_id)
            set_board_id(board.widget_common_id)
            output_success(f"Selected board: {board.name}")
    except ResolverError as e:
        output_error(str(e))
        raise typer.Exit(1)
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def current(
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output in JSON format"),
    ] = False,
) -> None:
    """Show the currently selected board."""
    board_id = get_board_id()
    if board_id is None:
        output_error("No board selected. Run 'favro board select <id>' first.")
        raise typer.Exit(1)

    try:
        with get_client() as client:
            resolver = BoardResolver(client)
            board = resolver.resolve(board_id)

            if json_output:
                output_json(board)
            else:
                output_success(
                    f"Current board: {board.name} ({board.widget_common_id})"
                )
    except ResolverError as e:
        output_error(str(e))
        raise typer.Exit(1)
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


def _render_board_view(
    board_name: str,
    columns: list[Column],
    cards: list[Card],
    max_cards: int,
    tags_map: dict[str, Tag] | None = None,
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
        table.add_column(f"{col.name} ({card_count})", width=200)

    # Determine max rows needed
    max_rows = (
        max(
            min(len(cards_by_column.get(col.column_id, [])), max_cards)
            for col in sorted_columns
        )
        if sorted_columns
        else 0
    )

    # Add rows
    for row_idx in range(max_rows):
        row_cells: list[str] = []
        for col in sorted_columns:
            col_cards = cards_by_column.get(col.column_id, [])
            if row_idx < len(col_cards):
                card = col_cards[row_idx]
                card_text = _format_card_cell(card, tags_map)
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


def _format_card_cell(card: Card, tags_map: dict[str, Tag] | None = None) -> str:
    """Format a card for display in a table cell."""
    lines: list[str] = []

    # Card identifier and name
    lines.append(f"[bold]\\[#{card.sequential_id}][/bold] {card.name[:200]}")

    # Truncate name if too long
    if len(card.name) > 200:
        lines[0] = f"[bold]\\[#{card.sequential_id}][/bold] {card.name[:197]}..."

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

    # Show tags if any
    if card.tags and tags_map:
        tag_strs: list[str] = []
        for tid in card.tags:
            if tid in tags_map:
                tag = tags_map[tid]
                if tag.color:
                    tag_strs.append(f"[{tag.color}]{tag.name}[/{tag.color}]")
                else:
                    tag_strs.append(tag.name)
        if tag_strs:
            lines.append("")
            lines.append(", ".join(tag_strs))

    return "\n".join(lines)
