# Setup and run guide

This guide takes the repository from a checkout to a running bot. It covers the native path and the Docker path.

## Prerequisites

- Git.
- uv, the package manager for this project. Install it with the official installer at docs.astral.sh/uv.
- A Discord bot application. Copy the application ID and generate a token. Enable the intents for message content, server members, and presence.
- Docker with the Compose plugin, only for the Docker path.

## Get the code

1. Clone the repository: `git clone git@github.com:hickwhither/TBCDISCORDPY.git`
2. Enter the directory: `cd TBCDISCORDPY`

## Create the .env file

1. Copy the example file: `cp example.env .env`.
2. Fill the three required values:

```
BOT_ID=123456789012345678
BOT_TOKEN=your-bot-token-here
PREFIX=!
```

Never commit the .env file. Git ignores it.

## Install the dependencies

Run `uv sync`. This installs the pinned packages into the project virtual environment, including ruff.

## Set up the database

The bot creates the database on its own. It runs `alembic upgrade head` at startup and backs up the current file to data/backups. To migrate before the first run, run `uv run alembic upgrade head`.

## Run the bot

Native:

```
uv run python main.py
```

Docker:

```
docker compose build
docker compose up -d
docker compose logs -f bot
```

## Make sure that the bot works

Run `!ping` in a channel the bot can see. A pong embed appears. The logs show `Loaded` lines and no `Error` lines.

## Owner commands that set up each feature

| Feature | Command | What it does |
|---|---|---|
| tickets | `!ticketsetup` | sends a create-ticket panel to the current channel |
| serverinfo | `!serverinfosetup` | posts the auto-updating info panel to the current channel |
| tempvoice | `!createvoice` | marks the current voice channel as the room trigger |
| antiraid | `!mark` | marks the current text channel for auto-ban |
| connhen | `!addconnhen @user 100` | grants currency for tests or a backfill |
| dev | `!sync` | syncs the command tree for the hard-coded guild |

## Troubleshooting

The bot raises `KeyError: 'BOT_TOKEN'` at startup. The cause is a missing .env file, or an empty value for one of BOT_ID, BOT_TOKEN, or PREFIX.

The startup log shows `SyntaxError: multiple exception types must be parenthesized` on the current master. Fix the Python 2 style except clauses, as README.md explains.

The `docker compose up` command fails when the .env file is missing. Create the file from example.env first.

Voice rooms need the Manage Channels and Move Members permissions. The Docker image already ships ffmpeg and libopus for audio.