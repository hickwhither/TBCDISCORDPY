# TBC Discord Bot

This is a hobby Discord bot for a personal server. It answers users in Vietnamese. The bot runs on the discord.py library. Its features include a connhen economy, temporary voice rooms, private tickets, anti-raid channels, server info panels, and server logging.

## Documentation

- The setup and run guide: docs/setup.md
- The architecture overview: docs/architecture.md

## Quick start

1. Install the dependencies: `uv sync`
2. Create the environment: `cp example.env .env`, then fill in BOT_ID, BOT_TOKEN, and PREFIX.
3. Run the bot: `uv run python main.py`

For Docker, run `docker compose build` and `docker compose up -d`.

Note for the current master: at commit 1292f19, most extensions fail to load because several files use Python 2 style except clauses. The architecture document lists the affected files and the fix.