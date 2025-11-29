"""Organization commands."""

from typing import Annotated

import typer

from favro_cli.api.client import FavroAPIError, FavroAuthError, FavroClient
from favro_cli.config import (
    get_credentials,
    get_organization_id,
    set_organization_id,
)
from favro_cli.output.formatters import (
    output_error,
    output_json,
    output_success,
    output_table,
)
from favro_cli.resolvers import OrganizationResolver, ResolverError
from favro_cli.state import state


app = typer.Typer(
    help="Organization commands",
    context_settings={"help_option_names": ["-h", "--help"]},
)


def get_client() -> FavroClient:
    """Get an authenticated client."""
    creds = get_credentials()
    if creds is None:
        output_error("Not logged in. Run 'favro login' first.")
        raise typer.Exit(1)

    email, token = creds
    org_id = get_organization_id()
    return FavroClient(email, token, org_id)


@app.command("list")
def list_orgs() -> None:
    """List all organizations."""
    creds = get_credentials()
    if creds is None:
        output_error("Not logged in. Run 'favro login' first.")
        raise typer.Exit(1)

    email, token = creds
    current_org = get_organization_id()

    try:
        # Don't include org header for listing orgs
        with FavroClient(email, token) as client:
            orgs = client.get_organizations()

            if state["json"]:
                output_json(orgs)
            else:
                # Add marker for current org
                for org in orgs:
                    if current_org and org.organization_id == current_org:
                        org.name = f"* {org.name}"

                output_table(
                    orgs,
                    [
                        ("organization_id", "ID"),
                        ("name", "Name"),
                    ],
                    title="Organizations (* = selected)",
                )
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)


@app.command()
def select(
    organization_id: Annotated[
        str,
        typer.Argument(help="Organization ID or name"),
    ],
) -> None:
    """Select an organization as default."""
    creds = get_credentials()
    if creds is None:
        output_error("Not logged in. Run 'favro login' first.")
        raise typer.Exit(1)

    email, token = creds

    try:
        # Resolve by ID or name
        with FavroClient(email, token) as client:
            resolver = OrganizationResolver(client)
            org = resolver.resolve(organization_id)
            set_organization_id(org.organization_id)
            output_success(f"Selected organization: {org.name}")
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
def current() -> None:
    """Show the currently selected organization."""
    org_id = get_organization_id()
    if org_id is None:
        output_error("No organization selected. Run 'favro org select <id>' first.")
        raise typer.Exit(1)

    creds = get_credentials()
    if creds is None:
        output_error("Not logged in. Run 'favro login' first.")
        raise typer.Exit(1)

    email, token = creds

    try:
        with FavroClient(email, token, org_id) as client:
            org = client.get_organization(org_id)

            if state["json"]:
                output_json(org)
            else:
                output_success(f"Current organization: {org.name} ({org.organization_id})")
    except FavroAuthError as e:
        output_error(e.message)
        raise typer.Exit(1)
    except FavroAPIError as e:
        output_error(f"API error: {e.message}")
        raise typer.Exit(1)
