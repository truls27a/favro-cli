"""Card commands."""

from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from favro_cli.api.client import FavroAPIError, FavroAuthError, FavroClient
from favro_cli.api.models import Card
from favro_cli.config import get_credentials, get_organization_id
from favro_cli.output.formatters import (
    output_error,
    output_json,
    output_success,
    output_table,
)
from favro_cli.resolvers import (
    BoardResolver,
    CardResolver,
    ColumnResolver,
    ResolverError,
    TagResolver,
    UserResolver,
)
from favro_cli.state import state


app = typer.Typer(help="Card commands")
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
def list_cards(
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Filter by board ID or name"),
    ] = None,
    column_id: Annotated[
        str | None,
        typer.Option("--column", "-c", help="Filter by column ID or name (requires --board for name)"),
    ] = None,
    collection_id: Annotated[
        str | None,
        typer.Option("--collection", help="Filter by collection ID"),
    ] = None,
) -> None:
    """List cards with optional filters."""
    if not board_id and not column_id and not collection_id:
        output_error("At least one filter is required: --board, --column, or --collection")
        raise typer.Exit(1)

    try:
        with get_client() as client:
            # Resolve board if provided
            resolved_board_id: str | None = None
            if board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(board_id)
                resolved_board_id = board.widget_common_id

            # Resolve column if provided (requires board for name lookup)
            resolved_column_id: str | None = None
            if column_id:
                column_resolver = ColumnResolver(client)
                column = column_resolver.resolve(column_id, board_id=resolved_board_id)
                resolved_column_id = column.column_id

            cards = client.get_cards(
                widget_common_id=resolved_board_id,
                column_id=resolved_column_id,
                collection_id=collection_id,
            )

            if state["json"]:
                output_json(cards)
            else:
                output_table(
                    cards,
                    [
                        ("sequential_id", "#"),
                        ("name", "Name"),
                        ("tasks_done", "Done"),
                        ("tasks_total", "Total"),
                    ],
                    title="Cards",
                )
    except (ResolverError, ValueError) as e:
        output_error(str(e))
        raise typer.Exit(1)
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def show(
    card_id: Annotated[
        str,
        typer.Argument(help="Card ID, sequential ID (#123), or name"),
    ],
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Board ID or name (narrows search scope)"),
    ] = None,
) -> None:
    """Show detailed card information."""
    try:
        with get_client() as client:
            # Resolve board if provided
            resolved_board_id: str | None = None
            if board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(board_id)
                resolved_board_id = board.widget_common_id

            card_resolver = CardResolver(client)
            card = card_resolver.resolve(card_id, board_id=resolved_board_id)

            if state["json"]:
                output_json(card)
            else:
                _render_card_detail(card)
    except (ResolverError, ValueError) as e:
        output_error(str(e))
        raise typer.Exit(1)
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


def _render_card_detail(card: Card) -> None:
    """Render detailed card view."""
    # Header info
    lines: list[str] = [
        f"[bold]#{card.sequential_id}[/bold] {card.name}",
        "",
        f"[dim]Card ID:[/dim] {card.card_id}",
        f"[dim]Common ID:[/dim] {card.card_common_id}",
    ]

    if card.widget_common_id:
        lines.append(f"[dim]Board:[/dim] {card.widget_common_id}")
    if card.column_id:
        lines.append(f"[dim]Column:[/dim] {card.column_id}")

    # Dates
    if card.start_date:
        lines.append(f"[dim]Start:[/dim] {card.start_date.strftime('%Y-%m-%d')}")
    if card.due_date:
        lines.append(f"[dim]Due:[/dim] {card.due_date.strftime('%Y-%m-%d')}")

    # Assignments
    if card.assignments:
        user_ids = [a.user_id for a in card.assignments]
        lines.append(f"[dim]Assigned:[/dim] {', '.join(user_ids)}")

    # Tags
    if card.tags:
        lines.append(f"[dim]Tags:[/dim] {', '.join(card.tags)}")

    # Tasks
    if card.tasks_total > 0:
        lines.append(f"[dim]Tasks:[/dim] {card.tasks_done}/{card.tasks_total}")

    # Comments
    if card.num_comments > 0:
        lines.append(f"[dim]Comments:[/dim] {card.num_comments}")

    panel = Panel("\n".join(lines), title=f"Card #{card.sequential_id}")
    console.print(panel)

    # Description
    if card.detailed_description:
        console.print()
        console.print("[bold]Description:[/bold]")
        md = Markdown(card.detailed_description)
        console.print(md)


@app.command()
def create(
    name: Annotated[
        str,
        typer.Argument(help="Card name"),
    ],
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Board ID or name"),
    ] = None,
    column_id: Annotated[
        str | None,
        typer.Option("--column", "-c", help="Column ID or name (requires --board for name)"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Card description"),
    ] = None,
) -> None:
    """Create a new card."""
    try:
        with get_client() as client:
            # Resolve board if provided
            resolved_board_id: str | None = None
            if board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(board_id)
                resolved_board_id = board.widget_common_id

            # Resolve column if provided (requires board for name lookup)
            resolved_column_id: str | None = None
            if column_id:
                column_resolver = ColumnResolver(client)
                column = column_resolver.resolve(column_id, board_id=resolved_board_id)
                resolved_column_id = column.column_id

            card = client.create_card(
                name=name,
                widget_common_id=resolved_board_id,
                column_id=resolved_column_id,
                detailed_description=description,
            )

            if state["json"]:
                output_json(card)
            else:
                output_success(f"Created card #{card.sequential_id}: {card.name}")
    except (ResolverError, ValueError) as e:
        output_error(str(e))
        raise typer.Exit(1)
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def update(
    card_id: Annotated[
        str,
        typer.Argument(help="Card ID, sequential ID (#123), or name"),
    ],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="New card name"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="New description"),
    ] = None,
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Board ID or name (narrows search scope)"),
    ] = None,
) -> None:
    """Update a card's properties."""
    if name is None and description is None:
        output_error("At least one of --name or --description must be provided")
        raise typer.Exit(1)

    try:
        with get_client() as client:
            # Resolve board if provided
            resolved_board_id: str | None = None
            if board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(board_id)
                resolved_board_id = board.widget_common_id

            card_resolver = CardResolver(client)
            card = card_resolver.resolve(card_id, board_id=resolved_board_id)

            card = client.update_card(
                card_id=card.card_id,
                name=name,
                detailed_description=description,
            )

            if state["json"]:
                output_json(card)
            else:
                output_success(f"Updated card #{card.sequential_id}: {card.name}")
    except (ResolverError, ValueError) as e:
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
    card_id: Annotated[
        str,
        typer.Argument(help="Card ID, sequential ID (#123), or name"),
    ],
    column_id: Annotated[
        str,
        typer.Option("--column", "-c", help="Target column ID or name", prompt=True),
    ],
    board_id: Annotated[
        str,
        typer.Option("--board", "-b", help="Board ID or name", prompt=True),
    ],
) -> None:
    """Move a card to a different column."""
    try:
        with get_client() as client:
            # Resolve board
            board_resolver = BoardResolver(client)
            board = board_resolver.resolve(board_id)
            resolved_board_id = board.widget_common_id

            # Resolve card
            card_resolver = CardResolver(client)
            card = card_resolver.resolve(card_id, board_id=resolved_board_id)

            # Resolve column
            column_resolver = ColumnResolver(client)
            column = column_resolver.resolve(column_id, board_id=resolved_board_id)

            card = client.update_card(
                card_id=card.card_id,
                column_id=column.column_id,
                widget_common_id=resolved_board_id,
            )

            if state["json"]:
                output_json(card)
            else:
                output_success(f"Moved card #{card.sequential_id} to column '{column.name}'")
    except (ResolverError, ValueError) as e:
        output_error(str(e))
        raise typer.Exit(1)
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def assign(
    card_id: Annotated[
        str,
        typer.Argument(help="Card ID, sequential ID (#123), or name"),
    ],
    user_id: Annotated[
        str | None,
        typer.Option("--add", "-a", help="User ID, name, or email to assign"),
    ] = None,
    remove_user_id: Annotated[
        str | None,
        typer.Option("--remove", "-r", help="User ID, name, or email to unassign"),
    ] = None,
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Board ID or name (narrows card search scope)"),
    ] = None,
) -> None:
    """Assign or unassign users to a card."""
    if user_id is None and remove_user_id is None:
        output_error("Either --add or --remove must be provided")
        raise typer.Exit(1)

    try:
        with get_client() as client:
            # Resolve board if provided
            resolved_board_id: str | None = None
            if board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(board_id)
                resolved_board_id = board.widget_common_id

            # Resolve card
            card_resolver = CardResolver(client)
            card = card_resolver.resolve(card_id, board_id=resolved_board_id)

            # Resolve users
            user_resolver = UserResolver(client)
            add_list: list[str] | None = None
            remove_list: list[str] | None = None
            add_user_name: str | None = None
            remove_user_name: str | None = None

            if user_id:
                resolved_user = user_resolver.resolve(user_id)
                add_list = [resolved_user.user_id]
                add_user_name = resolved_user.name

            if remove_user_id:
                resolved_user = user_resolver.resolve(remove_user_id)
                remove_list = [resolved_user.user_id]
                remove_user_name = resolved_user.name

            card = client.update_card(
                card_id=card.card_id,
                add_assignments=add_list,
                remove_assignments=remove_list,
            )

            if state["json"]:
                output_json(card)
            else:
                if add_user_name:
                    output_success(f"Assigned '{add_user_name}' to card #{card.sequential_id}")
                if remove_user_name:
                    output_success(f"Unassigned '{remove_user_name}' from card #{card.sequential_id}")
    except (ResolverError, ValueError) as e:
        output_error(str(e))
        raise typer.Exit(1)
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def tag(
    card_id: Annotated[
        str,
        typer.Argument(help="Card ID, sequential ID (#123), or name"),
    ],
    add_tag: Annotated[
        str | None,
        typer.Option("--add", "-a", help="Tag ID or name to add"),
    ] = None,
    remove_tag: Annotated[
        str | None,
        typer.Option("--remove", "-r", help="Tag ID or name to remove"),
    ] = None,
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Board ID or name (narrows card search scope)"),
    ] = None,
) -> None:
    """Add or remove tags from a card."""
    if add_tag is None and remove_tag is None:
        output_error("Either --add or --remove must be provided")
        raise typer.Exit(1)

    try:
        with get_client() as client:
            # Resolve board if provided
            resolved_board_id: str | None = None
            if board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(board_id)
                resolved_board_id = board.widget_common_id

            # Resolve card
            card_resolver = CardResolver(client)
            card = card_resolver.resolve(card_id, board_id=resolved_board_id)

            # Resolve tags
            tag_resolver = TagResolver(client)
            add_list: list[str] | None = None
            remove_list: list[str] | None = None
            add_tag_name: str | None = None
            remove_tag_name: str | None = None

            if add_tag:
                resolved_tag = tag_resolver.resolve(add_tag)
                add_list = [resolved_tag.tag_id]
                add_tag_name = resolved_tag.name

            if remove_tag:
                resolved_tag = tag_resolver.resolve(remove_tag)
                remove_list = [resolved_tag.tag_id]
                remove_tag_name = resolved_tag.name

            card = client.update_card(
                card_id=card.card_id,
                add_tags=add_list,
                remove_tags=remove_list,
            )

            if state["json"]:
                output_json(card)
            else:
                if add_tag_name:
                    output_success(f"Added tag '{add_tag_name}' to card #{card.sequential_id}")
                if remove_tag_name:
                    output_success(f"Removed tag '{remove_tag_name}' from card #{card.sequential_id}")
    except (ResolverError, ValueError) as e:
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
    card_id: Annotated[
        str,
        typer.Argument(help="Card ID, sequential ID (#123), or name"),
    ],
    board_id: Annotated[
        str | None,
        typer.Option("--board", "-b", help="Board ID or name (narrows card search scope)"),
    ] = None,
    everywhere: Annotated[
        bool,
        typer.Option("--everywhere", "-e", help="Delete from all boards"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation"),
    ] = False,
) -> None:
    """Delete a card."""
    try:
        with get_client() as client:
            # Resolve board if provided
            resolved_board_id: str | None = None
            if board_id:
                board_resolver = BoardResolver(client)
                board = board_resolver.resolve(board_id)
                resolved_board_id = board.widget_common_id

            # Resolve card
            card_resolver = CardResolver(client)
            card = card_resolver.resolve(card_id, board_id=resolved_board_id)

            if not force:
                confirm = typer.confirm(f"Are you sure you want to delete card #{card.sequential_id}: {card.name}?")
                if not confirm:
                    raise typer.Abort()

            client.delete_card(card.card_id, everywhere=everywhere)
            output_success(f"Deleted card #{card.sequential_id}: {card.name}")
    except (ResolverError, ValueError) as e:
        output_error(str(e))
        raise typer.Exit(1)
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)
