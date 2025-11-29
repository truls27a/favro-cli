"""Authentication commands."""

from typing import Annotated

import typer
from rich.prompt import Prompt

from favro_cli.api.client import FavroAPIError, FavroAuthError, FavroClient
from favro_cli.config import clear_credentials, get_credentials, get_organization_id, set_credentials
from favro_cli.state import state
from favro_cli.output.formatters import (
    output_error,
    output_info,
    output_json,
    output_panel,
    output_success,
    output_table,
)


app = typer.Typer(
    help="Authentication commands",
    context_settings={"help_option_names": ["-h", "--help"]},
)


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
            orgs = client.get_organizations()
            set_credentials(email, token)
            output_success(f"Logged in successfully. You have access to {len(orgs)} organization(s).")
    except FavroAuthError as e:
        output_error(e.message)
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
    org_id = get_organization_id()

    try:
        if org_id is None:
            # No org selected - show email and list accessible orgs
            with FavroClient(email, token) as client:
                orgs = client.get_organizations()

                if state["json"]:
                    output_json({"email": email, "organizations": [o.model_dump(by_alias=True) for o in orgs]})
                else:
                    output_info(f"[bold]Email:[/bold] {email}")
                    output_info("[bold]Organization:[/bold] [dim]None selected[/dim]")
                    output_info("")
                    output_table(
                        orgs,
                        [
                            ("organization_id", "Organization ID"),
                            ("name", "Name"),
                        ],
                        title="Accessible Organizations",
                    )
        else:
            # Org selected - fetch users and find current user by email
            with FavroClient(email, token, org_id) as client:
                users = client.get_users()
                current_user = next((u for u in users if u.email == email), None)

                if current_user is None:
                    output_error(f"Could not find user with email {email} in this organization.")
                    raise typer.Exit(1)

                if state["json"]:
                    output_json(current_user)
                else:
                    output_panel(
                        current_user,
                        [
                            ("user_id", "User ID"),
                            ("name", "Name"),
                            ("email", "Email"),
                            ("organization_role", "Role"),
                        ],
                        title="Current User",
                    )
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)
