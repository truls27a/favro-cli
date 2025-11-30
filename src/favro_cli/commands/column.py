"""Column commands."""

from typing import Annotated

import typer

from favro_cli.api.client import FavroAPIError, FavroAuthError
from favro_cli.commands.common import get_client
from favro_cli.config import get_board_id
from favro_cli.output.formatters import (
    output_error,
    output_json,
    output_success,
    output_table,
)
from favro_cli.resolvers import BoardResolver, ColumnResolver, ResolverError


app = typer.Typer(
    help="Column commands",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.command("list")
def list_columns(
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Board ID or name"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output in JSON format"),
    ] = False,
) -> None:
    """List columns for a board."""
    # Use default board if not specified
    effective_board_id = board_id or get_board_id()

    if not effective_board_id:
        output_error(
            "Board is required. Use --board or set a default with 'favro board select <id>'."
        )
        raise typer.Exit(1)

    try:
        with get_client() as client:
            board_resolver = BoardResolver(client)
            board = board_resolver.resolve(effective_board_id)
            columns = client.get_columns(board.widget_common_id)

            # Sort by position
            columns = sorted(columns, key=lambda c: c.position)

            if json_output:
                output_json(columns)
            else:
                output_table(
                    columns,
                    [
                        ("column_id", "ID"),
                        ("name", "Name"),
                        ("position", "Position"),
                        ("card_count", "Cards"),
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
def create(
    name: Annotated[
        str,
        typer.Argument(help="Column name"),
    ],
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Board ID or name"),
    ] = None,
    position: Annotated[
        int | None,
        typer.Option("--position", "-p", help="Column position (0-indexed)"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output in JSON format"),
    ] = False,
) -> None:
    """Create a new column on a board."""
    # Use default board if not specified
    effective_board_id = board_id or get_board_id()

    if not effective_board_id:
        output_error(
            "Board is required. Use --board or set a default with 'favro board select <id>'."
        )
        raise typer.Exit(1)

    try:
        with get_client() as client:
            board_resolver = BoardResolver(client)
            board = board_resolver.resolve(effective_board_id)
            column = client.create_column(
                widget_common_id=board.widget_common_id,
                name=name,
                position=position,
            )

            if json_output:
                output_json(column)
            else:
                output_success(f"Created column: {column.name} (position {column.position})")
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
def rename(
    column_id: Annotated[
        str,
        typer.Argument(help="Column ID or name"),
    ],
    name: Annotated[
        str,
        typer.Argument(help="New column name"),
    ],
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Board ID or name (required for name lookup)"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output in JSON format"),
    ] = False,
) -> None:
    """Rename a column."""
    # Use default board if not specified
    effective_board_id = board_id or get_board_id()

    try:
        with get_client() as client:
            # Resolve board first if provided (needed for column name lookup)
            resolved_board_id: str | None = None
            if effective_board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(effective_board_id)
                resolved_board_id = board.widget_common_id

            column_resolver = ColumnResolver(client)
            column = column_resolver.resolve(column_id, board_id=resolved_board_id)

            column = client.update_column(
                column_id=column.column_id,
                name=name,
            )

            if json_output:
                output_json(column)
            else:
                output_success(f"Renamed column to: {column.name}")
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
def move(
    column_id: Annotated[
        str,
        typer.Argument(help="Column ID or name"),
    ],
    position: Annotated[
        int,
        typer.Argument(help="New position (0-indexed)"),
    ],
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Board ID or name (required for name lookup)"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output in JSON format"),
    ] = False,
) -> None:
    """Move a column to a different position."""
    # Use default board if not specified
    effective_board_id = board_id or get_board_id()

    try:
        with get_client() as client:
            # Resolve board first if provided (needed for column name lookup)
            resolved_board_id: str | None = None
            if effective_board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(effective_board_id)
                resolved_board_id = board.widget_common_id

            column_resolver = ColumnResolver(client)
            column = column_resolver.resolve(column_id, board_id=resolved_board_id)

            column = client.update_column(
                column_id=column.column_id,
                position=position,
            )

            if json_output:
                output_json(column)
            else:
                output_success(f"Moved column '{column.name}' to position {column.position}")
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
def delete(
    column_id: Annotated[
        str,
        typer.Argument(help="Column ID or name"),
    ],
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Board ID or name (required for name lookup)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation"),
    ] = False,
) -> None:
    """Delete a column and all its cards."""
    # Use default board if not specified
    effective_board_id = board_id or get_board_id()

    if not force:
        confirm = typer.confirm(
            "Are you sure? This will delete the column and all its cards."
        )
        if not confirm:
            raise typer.Abort()

    try:
        with get_client() as client:
            # Resolve board first if provided (needed for column name lookup)
            resolved_board_id: str | None = None
            if effective_board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(effective_board_id)
                resolved_board_id = board.widget_common_id

            column_resolver = ColumnResolver(client)
            column = column_resolver.resolve(column_id, board_id=resolved_board_id)

            client.delete_column(column.column_id)
            output_success(f"Deleted column '{column.name}'")
    except ResolverError as e:
        output_error(str(e))
        raise typer.Exit(1)
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)
