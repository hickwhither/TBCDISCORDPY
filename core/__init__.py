import datetime
import os

import discord
from discord import Message
from discord.ext import commands
from discord.ext.commands import Bot

from core import config

from .database import init_db

TBC = Bot(
    command_prefix=config.PREFIX,
    intents=discord.Intents.all(),
    application_id=config.BOT_ID,
    help_command=None,
)


@TBC.event
async def on_message(message: Message):
    if message.content.startswith(config.PREFIX):
        message.content = config.PREFIX + message.content[len(config.PREFIX) :].strip()
        await TBC.process_commands(message)


@TBC.event
async def setup_hook():
    extra_log = []
    for file in os.listdir("features"):
        if not file.startswith("_") and os.path.exists(os.path.join("features", file)):
            if file.endswith(".py"):
                file = file[:-3]
            try:
                await TBC.load_extension(f"features.{file}")
                print(f"✅ Loaded {file}")
            except Exception as e:
                print(f"❌ Error {file}: {e}")
    await init_db()
    print()
    for extra in extra_log:
        print(f"From {extra[0]}:\n{extra[1]}")


@TBC.event
async def on_ready():
    global start_timestamp
    start_timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    print(f"=== Logged as {TBC.user} ({TBC.user.id}) ===")


@TBC.command(aliases=["uptime", "latency"])
async def ping(ctx: commands.Context):
    uptime_relative = f"<t:{start_timestamp}:R>"
    uptime_full = f"<t:{start_timestamp}:F>"
    api_ping = round(TBC.latency * 1000)

    embed = discord.Embed(title="🏓 Pong!", color=discord.Color.blue())
    embed.add_field(name="Latency", value=f"`{api_ping} ms`", inline=True)
    embed.add_field(
        name="Uptime", value=f"{uptime_full}\n{uptime_relative}", inline=True
    )
    await ctx.send(embed=embed)
