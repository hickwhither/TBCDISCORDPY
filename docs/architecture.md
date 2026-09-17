# Architecture

TBC is a Discord bot that answers users in Vietnamese.

It runs on these tools:

- Python 3.14, managed by uv.
- discord.py 2.7.1 or newer.
- SQLite for data, through async SQLAlchemy 2.
- Alembic for the schema changes.
- Docker and Docker Compose for deployment.
- Ruff for lint and format checks.

## Repository layout

```
main.py                  Entry point (3 lines)
core/                    Shared framework
  __init__.py            The bot client (TBC), startup, global handlers, ping command
  config.py              Environment configuration (BOT_ID, BOT_TOKEN, PREFIX, LOG_CHANNEL_ID)
  database.py            Async engine, session factory, Base, backup, init_db
  utils.py               Shared helpers (reply_ephemeral, resolve_member)
features/                Per-feature cogs, the project calls them extensions
  antiraid/              Marks a channel and auto-bans anyone who posts there
  birthday/              Celebrates member birthdays in a channel the admin configures
  connhen/               Fun economy currency named connhen
  dev.py                 Owner utilities (sync, reload)
  help.py                Custom help command
  serverinfo/            Auto-updating server info panel plus info command
  serverlog/             Event log that sends to a channel
  tempvoice/             Per-user temporary voice rooms with a control panel
  tickets/               Private ticket channels
    <feature>/__init__.py     The cog and its async setup function
    <feature>/models.py       SQLAlchemy models on the shared Base
    <feature>/repository.py   Query functions, one session per call
    <feature>/service.py      Business logic
    <feature>/views/          discord.ui views, modals, and embeds
migrations/              Alembic scripts, alembic.ini sits at the repo root
Dockerfile, docker-compose.yml, example.env
.github/workflows/       ruff.yml (lint) and tbcoj.yml (deploy)
```

## Startup

main.py imports the TBC client and the configuration from the core package, then runs the bot with the token. The setup_hook does two jobs when the bot logs in:

1. It upgrades the database with `alembic upgrade head` and backs up the old file to data/backups.
2. It loads every entry under features/ that does not start with an underscore.

core/config.py reads BOT_ID, BOT_TOKEN, and PREFIX from the environment. These three have no defaults. A missing value crashes the bot at import time.

## Features

Each feature is an extension. It exposes a top-level async function named setup that takes the bot and registers the cogs with bot.add_cog. A feature package keeps its cog and setup in __init__.py, the models in models.py, the queries in repository.py, the logic in service.py, and the interactive parts in views/.

## Data

The default database is data/tbc.db. The migration head is 888d5bd70151. To change the schema, edit the model, then run `uv run alembic revision --autogenerate -m "describe the change"` and review the generated file. The bot applies new migrations at startup.

There is a gap in autogenerate. migrations/env.py imports the models for antiraid, birthday, tempvoice, and tickets, but not connhen and serverinfo. Add those imports before you autogenerate, or the tool will not see changes to those models.

## Configuration

core/config.py loads a dotenv file first, then reads the variables from the environment. example.env lists the whole set.

| Variable | Required | Default | Used by |
|---|---|---|---|
| `BOT_ID` | yes | none | core/__init__.py, the application_id value |
| `BOT_TOKEN` | yes | none | core/__init__.py, when it runs the bot |
| `PREFIX` | yes | none | the command prefix, for example `!` |
| `DATABASE_URL` | no | `sqlite+aiosqlite:///data/tbc.db` | core/database.py and migrations/env.py |
| `LOG_CHANNEL_ID` | no | `0` | core/config.py, then the serverlog feature |
| `TEMP_VOICE_TRIGGER` | no | `Create Voice` | the tempvoice trigger channel name |
| `TEMP_VOICE_ROOM_TEMPLATE` | no | `{name}'s Room` | the tempvoice room naming |
| `TEMP_VOICE_IMAGE` | no | empty | the tempvoice panel thumbnail URL |
| `TICKET_STAFF_ROLE` | no | `Staff` | the role that counts as staff |
| `TICKET_AUTO_CLOSE_HOURS` | no | `24` | the auto-close delay |
| `TICKET_WARN_BEFORE_MINUTES` | no | `30` | the warning before auto-close |
| `TICKET_CHECK_INTERVAL_MINUTES` | no | `15` | the background sweep interval |
| `TICKET_MAX_PER_USER` | no | `2` | the open-ticket limit per user |
| `BIRTHDAY_TIMEZONE` | no | `Asia/Ho_Chi_Minh` | the timezone that decides if it is a member's birthday |
| `BIRTHDAY_GIFT_CONNHEN` | no | `500` | the connhen gift per birthday year, `0` disables gifts |

## Deployment

docker-compose.yml runs one service named bot. It builds from the Dockerfile, reads the configuration from .env, and mounts ./data to /app/data so the SQLite file survives rebuilds. The Dockerfile ships ffmpeg and libopus for voice.

The CI has two workflows. ruff.yml lints and formats every push and pull request. tbcoj.yml deploys on a push to master.

## Known issues

- Fourteen files use Python 2 style except clauses, for example `except discord.NotFound, discord.HTTPException:`. This is a syntax error in Python 3. Those features fail to load, and the ruff CI fails with code E999. The fix wraps each exception tuple in parentheses. The affected files are core/utils.py, features/antiraid/service.py, features/serverinfo/__init__.py, features/serverinfo/service.py, features/serverlog/service.py, features/tempvoice/__init__.py, features/tempvoice/service.py, features/tempvoice/views/actions.py, features/tempvoice/views/embed.py, features/tempvoice/views/modals.py, features/tickets/__init__.py, features/tickets/service.py, features/tickets/views/member.py, and features/tickets/views/panel.py.
- dev.py hard-codes one guild ID for the sync command. It works for that one guild only.
- The Docker healthcheck is a placeholder. It reports healthy even when the bot is not connected.
- docker-compose.yml uses `env_file: .env`. A local compose up fails until that file exists.