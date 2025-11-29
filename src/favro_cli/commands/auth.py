"""Authentication commands."""

from typing import Annotated

import typer
from rich.prompt import Prompt

from favro_cli.api.client import FavroAPIError, FavroAuthError, FavroClient
from favro_cli.config import clear_credentials, get_credentials, set_credentials
from favro_cli.state import state
from favro_cli.output.formatters import (
    output_error,
    output_json,
    output_panel,
    output_success,
)


app = typer.Typer(help="Authentication commands")


@app.command()
def login(
    email: Annotated[
        str | None,
        typer.Option("--email", "-e", help="Favro account email"),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option("--token", "-t", help="Favro API token"),
    ] = None,
) -> None:
    """Login to Favro by saving credentials."""
    if email is None:
        email = Prompt.ask("Email")
    if token is None:
        token = Prompt.ask("API Token", password=True)

    # Validate credentials by making an API call
    try:
        with FavroClient(email, token) as client:
            user = client.get_user("me")
            set_credentials(email, token)
            output_success(f"Logged in as {user.name} ({user.email})")
    except FavroAuthError:
        output_error("Invalid credentials")
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def logout() -> None:
    """Remove saved credentials."""
    creds = get_credentials()
    if creds is None:
        output_error("Not logged in")
        raise typer.Exit(1)

    clear_credentials()
    output_success("Logged out successfully")


@app.command()
def whoami() -> None:
    """Show current user information."""
    creds = get_credentials()
    if creds is None:
        output_error("Not logged in. Run 'favro login' first.")
        raise typer.Exit(1)

    email, token = creds

    try:
        with FavroClient(email, token) as client:
            user = client.get_user("me")

            if state["json"]:
                output_json(user)
            else:
                output_panel(
                    user,
                    [
                        ("user_id", "User ID"),
                        ("name", "Name"),
                        ("email", "Email"),
                    ],
                    title="Current User",
                )
    except FavroAuthError:
        output_error("Invalid credentials. Please login again.")
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)
