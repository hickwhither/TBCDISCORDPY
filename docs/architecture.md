# Architecture

This bot is a hobby Discord bot for a personal server. It uses the discord.py library, version 2.7.1 or newer. The project uses uv to manage dependencies. Data lives in a SQLite database. SQLAlchemy 2 handles the data access. Alembic handles the schema changes. The bot answers users in Vietnamese. This document maps the codebase so a fresh agent run can navigate it without guessing. For a run guide, read the setup document.

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
    <feature>/views/          discord.ui views, modals, and embeds for tempvoice and tickets
migrations/              Alembic scripts, alembic.ini sits at the repo root
Dockerfile, docker-compose.yml, example.env
.github/workflows/       ruff.yml (lint) and tbcoj.yml (deploy)
```

## Entry point and startup flow

main.py is the entry point. It imports the TBC client and the configuration from the core package, then runs the bot with the token.

The TBC client is created at import time in core/__init__.py. It uses these values:

- command_prefix: the PREFIX value from the configuration.
- intents: all intents that discord.py offers.
- application_id: the BOT_ID value from the configuration.
- help_command: none, because the help feature supplies its own help system.

The setup_hook event runs when the bot logs in. It does two jobs.

The first job is the database. It calls init_db from core/database.py. init_db does three things in order:

1. Create the data directory for SQLite when the DATABASE_URL value points to a file.
2. Back up the current database to data/backups. The backup keeps the newest 15 files.
3. Run `alembic upgrade head` to move the schema to the latest revision.

The second job is to load extensions. The loader iterates over the features directory. It skips any entry that starts with an underscore. For each other entry it calls TBC.load_extension. The extension name is features plus the entry name. Load failures are caught per extension and logged only. The bot still boots with the other features.

The on_message event overrides the normal prefix handling. If a message starts with the PREFIX value, the bot strips the prefix, changes the message content, and calls process_commands itself.

A global on_command_error handler catches command errors. It ignores CommandNotFound. It replies for NotOwner, CheckFailure, and UserInputError. For other errors it prints a traceback and replies a generic error message.

The on_ready event records start_timestamp and prints a log line. The ping command lives in core/__init__.py. It uses the aliases uptime and latency.

## How a feature is registered

A feature is a module or a package under features/. It must expose a top-level async function named setup that takes the bot. The function adds the feature cogs with bot.add_cog. There is no central registry. The loader picks up anything under features/ that does not start with an underscore.

The convention inside a sub-package:

- __init__.py: the cog class and the setup function.
- models.py: the SQLAlchemy models.
- repository.py: the query functions.
- service.py: the business logic.
- views/: the discord.ui parts for interactive panels.

The views packages re-export everything through their own __init__.py file.

## Data model and migrations

Persistence is async SQLAlchemy 2 against SQLite by default. The default URL is `sqlite+aiosqlite:///data/tbc.db`. core/database.py owns the async engine, the session factory, and the shared Base class. Each model sets extend_existing to True. Each model uses a BigInteger primary key for a Discord ID, with autoincrement off.

### Tables

The migration head is a71f9c3d2e05.

| Table | Model | Owned by | Purpose |
|---|---|---|---|
| `marked_channels` | `MarkedChannel` | `features/antiraid/models.py` | channels marked for auto-ban |
| `users_economy` | `UserEconomy` | `features/connhen/models.py` | connhen balance and daily cooldown |
| `temp_voice_channels` | `TempVoiceChannel` | `features/tempvoice/models.py` | per-user temporary voice rooms |
| `create_voice_channels` | `CreateVoiceChannel` | `features/tempvoice/models.py` | trigger channels that spawn rooms |
| `tickets` | `Ticket` | `features/tickets/models.py` | ticket channels and auto-close state |
| `ticket_panel_setup` | `TicketPanelSetup` | `features/tickets/models.py` | create-ticket panels |
| `server_info_panels` | `ServerInfoPanel` | `features/serverinfo/models.py` | live server info panels |

### Migration chain

alembic.ini sets the script location to migrations. migrations/env.py is async. It pulls the URL from the DATABASE_URL value and falls back to the SQLite default. It sets render_as_batch for SQLite ALTER statements and compare_type for type checks.

The history is a linear chain:

1. `b51c9cd83f6d`, the initial migration. It creates marked_channels and users_economy.
2. `3b22e11c3530`. It creates temp_voice_channels, ticket_panel_setup, and tickets.
3. `6f3f5b942ade`. It creates create_voice_channels.
4. `a71f9c3d2e05`, the head. It creates server_info_panels.

Note a gap in autogenerate. migrations/env.py imports the models for antiraid, tempvoice, and tickets. It does not import the models for connhen and serverinfo. Those two tables exist because the migrations were written for them by hand. If you autogenerate after you change a connhen or serverinfo model, Alembic will not see the change. It can even propose to drop that table. Add the model imports to migrations/env.py before you autogenerate.

### Make a schema change

1. Edit the model file under features/. The model registers on the shared Base.
2. Add the model import to migrations/env.py.
3. Run `uv run alembic revision --autogenerate -m "describe the change"` and review the generated file.
4. Run `uv run alembic upgrade head`, or restart the bot, because init_db upgrades automatically.
5. Add the migration in the same linear style as the existing files.

## Configuration through environment variables

core/config.py loads a dotenv file, then reads BOT_ID, BOT_TOKEN, and PREFIX with os.environ. It has no default for these three values. A missing value crashes the bot at import time. All other values are optional with defaults. example.env lists the whole set.

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

## Docker, CI, and deployment

The Dockerfile uses two stages. The builder installs uv and runs `uv sync --frozen --no-dev`. The runtime uses python:3.14-slim and installs libffi-dev, libopus0, and ffmpeg for voice. It copies the virtual environment from the builder and creates the data directory. The start command is `python main.py`. The healthcheck is a placeholder and always reports healthy.

docker-compose.yml defines one service named bot. It builds from the Dockerfile and loads the configuration from .env. The file must exist. It mounts ./data to /app/data, so the SQLite file survives rebuilds. The restart policy is unless-stopped.

The repo has two CI workflows:

- ruff.yml runs on push and on pull request. It syncs the environment, runs `ruff check .`, and runs `ruff format --check .`.
- tbcoj.yml runs on a push to master. It connects to a VPS over SSH with three secrets, VPS_HOST, VPS_USERNAME, and VPS_SSH_KEY. It resets the working tree to origin/master, builds the images, starts the service, and prunes old images. This is the production path.

## Background or periodic work

- tempvoice cleanup loop: runs every 60 seconds and deletes empty rooms and their rows. Rooms also delete when the last member leaves.
- tickets auto-check: a tasks.loop at the TICKET_CHECK_INTERVAL_MINUTES interval. It closes tickets that sit idle too long and warns before it closes them.
- serverinfo refresh: on_ready resyncs the panels. Listeners report member, role, and guild changes. A 3 second debounce in service.py limits the refresh rate.
- persistent views: tempvoice and tickets register their views again in on_ready, with the message_id, so the buttons survive restarts.

## Known issues and fragile spots

1. Broken except syntax, a blocker for most features. Fourteen files use Python 2 style except clauses, for example `except discord.NotFound, discord.HTTPException:`. This is a syntax error in Python 3. The modules fail to import, and the loader swallows the error per extension. The bot boots, but those features are missing. This is confirmed with `python -m compileall` on a fresh checkout at commit 1292f19.

   The affected files are core/utils.py, features/antiraid/service.py, features/serverinfo/__init__.py, features/serverinfo/service.py, features/serverlog/service.py, features/tempvoice/__init__.py, features/tempvoice/service.py, features/tempvoice/views/actions.py, features/tempvoice/views/embed.py, features/tempvoice/views/modals.py, features/tickets/__init__.py, features/tickets/service.py, features/tickets/views/member.py, and features/tickets/views/panel.py.

   Only connhen, dev, help, and ping load on this master. The ruff CI fails on this parse with code E999. The fix is mechanical. Wrap each exception tuple in parentheses. For example `except discord.NotFound, discord.HTTPException:` becomes `except (discord.NotFound, discord.HTTPException):`. A small PR fixes this and unblocks CI.

2. Everything under features/ is an extension. Any entry that does not start with an underscore is loaded and must define `async def setup(bot)`. A plain helper module under features/ fails on load and logs an error.

3. migrations/env.py omits the connhen and serverinfo models for autogenerate. See the migration chain section.

4. BOT_ID, BOT_TOKEN, and PREFIX have no defaults. A missing .env file fails fast at import time.

5. dev.py hard-codes one guild ID, 1275798785318064138, for the sync command. That works for that one guild only.

6. The backup uses the sqlite3 module. If DATABASE_URL points at another database, the backup does nothing and logs nothing, though Alembic still runs.

7. The on_message event re-implements command parsing and changes the message content. Keep this in mind when you add prefix commands.

8. The healthcheck in the Dockerfile and in compose is a placeholder. It reports healthy even when the bot is not connected.

9. docker-compose.yml uses `env_file: .env`. A local compose up fails until that file exists.

10. The containers do not mount the source code as a volume. Code changes need a rebuild, which the deploy workflow always does.

## Command reference

The user-facing text is Vietnamese.

| Command | Aliases | Access | Feature |
|---|---|---|---|
| `ping` | `uptime`, `latency` | all | core |
| `help` | `h` | all | help |
| `connhen` | `wallet`, `money`, `balance`, `bal` | all | connhen |
| `bangxephang` | `top` | all | connhen |
| `daily` | | all | connhen |
| `gamble` | `bet` | all | connhen |
| `pay` | | all | connhen |
| `addconnhen` | `give`, `grant`, `add` | owner | connhen |
| `mark`, `unmark`, `antilist` | | owner | antiraid |
| `createvoice` | | owner | tempvoice |
| `chaninfo` | | guild | tempvoice |
| `serverinfo` | `si`, `server`, `sv` | owner | serverinfo |
| `serverinfosetup`, `serverinfopanelremove` | | owner | serverinfo |
| `ticketsetup`, `ticketpanelremove` | | owner | tickets |
| `ticketlist`, `ticketadd`, `ticketremove` | | guild | tickets |
| `sync`, `reload` | `rl`, `yell` | owner | dev |