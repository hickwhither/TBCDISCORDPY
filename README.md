# TBC Discord Bot

TBC is a Discord bot that answers users in Vietnamese. It runs on Python and discord.py, uses uv for dependencies, SQLite for data, and Docker for deployment.

## Quick start

1. Install the dependencies: `uv sync`
2. Create the environment: `cp example.env .env`, then fill in BOT_ID, BOT_TOKEN, and PREFIX.
3. Run the bot: `uv run python main.py`

For Docker, run `docker compose build` and `docker compose up -d`.

## Documentation

- The setup and run guide: docs/setup.md
- The architecture overview: docs/architecture.md

## Note for the current master

At commit 1292f19, most extensions fail to load because several files use Python 2 style except clauses. docs/architecture.md lists the affected files and the fix.