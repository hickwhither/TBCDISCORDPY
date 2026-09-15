# Setup and run guide

This guide takes the repository from a checkout to a running bot. It covers the native path and the Docker path. For the code map, read the architecture document.

## Prerequisites

You need these tools and accounts:

- Git, to clone the repository.
- uv, the package manager for this project. Install it with the official installer at docs.astral.sh/uv. uv fetches the pinned Python 3.14 from .python-version when it is missing.
- A Discord bot application from the Discord Developer Portal. Copy the application ID and generate a token. Enable the privileged intents for message content, server members, and presence, because the code requests all intents.
- Docker with the Compose plugin, only for the Docker path.

## Get the code

1. Clone the repository: `git clone git@github.com:hickwhither/TBCDISCORDPY.git`.
2. Enter the directory: `cd TBCDISCORDPY`.

## Create the .env file

1. Copy the example file: `cp example.env .env`.
2. Fill the three required values. The bot exits at startup when one is missing:

```
BOT_ID=123456789012345678
BOT_TOKEN=your-bot-token-here
PREFIX=!
```

Leave DATABASE_URL at its default, `sqlite+aiosqlite:///data/tbc.db`, unless you have a reason to change it. The backup code in core/database.py works with SQLite only. The optional keys, LOG_CHANNEL_ID, TEMP_VOICE_IMAGE, and the TICKET_* keys, follow the table in the architecture document. Never commit the .env file. Git ignores it.

## Install the dependencies

Run `uv sync`. This installs the locked packages into the project virtual environment, including the dev group with ruff.

## Set up the database

You do not create the database by hand. The bot runs `alembic upgrade head` at startup through init_db in core/database.py. It creates the data directory too. To migrate before the first run, run `uv run alembic upgrade head`.

The database file lives at data/tbc.db. Each upgrade backs up the current file to data/backups and keeps the newest 15 backups.

## Run the bot natively

Run `uv run python main.py` in the project root.

Expected startup logs:

```
=== Logged as TBC#0000 (1234567890) ===
✅ Loaded connhen
✅ Loaded dev
```

Note for the current master. At commit 1292f19, most extensions fail to load. Fourteen files use Python 2 style except clauses, for example `except discord.NotFound, discord.HTTPException:`. This is a syntax error in Python 3. The startup log shows `❌ Error ... SyntaxError ...` lines for them. Only connhen, dev, help, and ping load until you fix it. Wrap each exception tuple in parentheses, and the full feature set returns. The architecture document lists every affected file.

## Run the bot in Docker

1. Create the .env file as described above. Compose reads it with env_file, and the command fails when the file is missing.
2. Build the image: `docker compose build`.
3. Start the service: `docker compose up -d`.
4. Read the logs: `docker compose logs -f bot`.

The mount of ./data to /app/data keeps the SQLite file across rebuilds. The service restarts unless you stop it. The healthcheck is a placeholder and always reports healthy.

## Make sure that the bot works

Run `!ping` in a channel the bot can see. A pong embed appears. Run `!help` and the help menu appears. The logs show `✅ Loaded` lines and no `❌ Error` lines.

## Owner commands that set up each feature

The server owner runs these in a channel. They create the panels and triggers the features need.

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

The startup log shows `❌ Error features.xxx ... SyntaxError: multiple exception types must be parenthesized` on the current master. Fix the except clauses, as the note above explains.

The `docker compose up` command fails with a message about a missing .env file. Create the file from example.env first.

Buttons do not work after a restart when the feature did not load or the panel message is gone. Recreate the panel with the setup command.

Voice rooms need the Manage Channels and Move Members permissions. The Docker image already ships ffmpeg and libopus for audio.