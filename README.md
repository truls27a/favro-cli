# favro-cli

Command line interface for Favro project management.

## Installation

```bash
pip install favro-cli
```

## Usage

```bash
# Authentication
favro login
favro logout
favro whoami

# Organizations
favro org list
favro org select <org-id>
favro org current

# Boards
favro board list
favro board show [board-id]
favro board view [board-id]
favro board select <board-id>
favro board current

# Cards
favro card list --board <board-id>
favro card show <card-id>
favro card create "Card name" --board <board-id>
favro card update <card-id> --name "New name"
favro card move <card-id> --column <column-id>
favro card assign <card-id> --add <user>
favro card tag <card-id> --add <tag>
favro card delete <card-id>

# Columns
favro column list --board <board-id>
favro column create "Column name" --board <board-id>
favro column rename <column-id> "New name" --board <board-id>
favro column move <column-id> <position> --board <board-id>
favro column delete <column-id> --board <board-id>
```

All commands support `--json` for machine-readable output.

Credentials are stored in `~/.config/favro-cli/config.toml`.
