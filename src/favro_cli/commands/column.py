"""Column commands."""

from typing import Annotated

import typer

from favro_cli.api.client import FavroAPIError, FavroAuthError, FavroClient
from favro_cli.config import get_credentials, get_organization_id
from favro_cli.output.formatters import (
    output_error,
    output_json,
    output_success,
    output_table,
)
from favro_cli.resolvers import BoardResolver, ColumnResolver, ResolverError
from favro_cli.state import state


app = typer.Typer(help="Column commands")


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
def list_columns(
    board_id: Annotated[
        str,
        typer.Option("--board", "-b", help="Board ID or name", prompt=True),
    ],
) -> None:
    """List columns for a board."""
    try:
        with get_client() as client:
            board_resolver = BoardResolver(client)
            board = board_resolver.resolve(board_id)
            columns = client.get_columns(board.widget_common_id)

            # Sort by position
            columns = sorted(columns, key=lambda c: c.position)

            if state["json"]:
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
        str,
        typer.Option("--board", "-b", help="Board ID or name", prompt=True),
    ],
    position: Annotated[
        int | None,
        typer.Option("--position", "-p", help="Column position (0-indexed)"),
    ] = None,
) -> None:
    """Create a new column on a board."""
    try:
        with get_client() as client:
            board_resolver = BoardResolver(client)
            board = board_resolver.resolve(board_id)
            column = client.create_column(
                widget_common_id=board.widget_common_id,
                name=name,
                position=position,
            )

            if state["json"]:
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
) -> None:
    """Rename a column."""
    try:
        with get_client() as client:
            # Resolve board first if provided (needed for column name lookup)
            resolved_board_id: str | None = None
            if board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(board_id)
                resolved_board_id = board.widget_common_id

            column_resolver = ColumnResolver(client)
            column = column_resolver.resolve(column_id, board_id=resolved_board_id)

            column = client.update_column(
                column_id=column.column_id,
                name=name,
            )

            if state["json"]:
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
) -> None:
    """Move a column to a different position."""
    try:
        with get_client() as client:
            # Resolve board first if provided (needed for column name lookup)
            resolved_board_id: str | None = None
            if board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(board_id)
                resolved_board_id = board.widget_common_id

            column_resolver = ColumnResolver(client)
            column = column_resolver.resolve(column_id, board_id=resolved_board_id)

            column = client.update_column(
                column_id=column.column_id,
                position=position,
            )

            if state["json"]:
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
            if board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(board_id)
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
