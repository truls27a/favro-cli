"""Common utilities for command modules."""

import typer

from favro_cli.api.client import FavroClient
from favro_cli.config import get_credentials, get_organization_id
from favro_cli.output.formatters import output_error


def get_client(require_org: bool = True) -> FavroClient:
    """Get an authenticated client.

    Args:
        require_org: If True, requires organization to be selected.
    """
    creds = get_credentials()
    if creds is None:
        output_error("Not logged in. Run 'favro login' first.")
        raise typer.Exit(1)

    org_id = get_organization_id() if require_org else None
    if require_org and org_id is None:
        output_error("No organization selected. Run 'favro org select <id>' first.")
        raise typer.Exit(1)

    email, token = creds
    return FavroClient(email, token, org_id)
