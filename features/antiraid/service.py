import discord
from features.antiraid import repository

MARK_MESSAGE = """
Tao được thằng {user_mention} mở lên và được dặn là thằng nào mà dám nhắn trong {channel_mention} thì tao sẽ ban luôn thằng đó khỏi server .
Hãy cân nhắc kẻo ngu ngu nhắn vô kênh này. 
Báo trước rồi nhé.
""".strip()


async def mark_channel(ctx: discord.ext.commands.Context) -> None:
    channel = ctx.channel
    existing = await repository.get_channel(channel.id)
    if existing:
        return await ctx.reply(f"{channel.mention} is already marked.")

    async with ctx.typing():
        embed = discord.Embed(
            title="🚨 ANTI-RAID 🚨",
            description=MARK_MESSAGE.format(
                user_mention=ctx.author.mention,
                channel_mention=channel.mention,
            ),
            color=discord.Color.red(),
        )
        embed.set_footer(text=f"Đã ban: 0")
        message = await ctx.send(embed=embed)

    await repository.add_channel(
        channel_id=channel.id,
        guild_id=ctx.guild.id,
        marked_by=ctx.author.id,
        message_id=message.id,
    )
    await ctx.message.delete()


async def unmark_channel(ctx: discord.ext.commands.Context) -> None:
    channel = ctx.channel
    row = await repository.get_channel(channel.id)
    if not row:
        return await ctx.reply(f"{channel.mention} Không có đánh dấu.")

    if row.message_id:
        try:
            message = await channel.fetch_message(row.message_id)
            await message.delete()
        except discord.NotFound:
            pass

    await repository.remove_channel(channel.id)
    await ctx.message.add_reaction("<:antiraid_disabled:1544363200726831284>")


async def get_marked_list(bot: discord.ext.commands.Bot) -> list[str]:
    rows = await repository.get_all()
    lines = []
    for row in rows:
        channel = bot.get_channel(row.channel_id)
        lines.append(channel.mention if channel else f"<#{row.channel_id}> (deleted)")
    return lines


async def check_ban(message: discord.Message) -> None:
    
    if message.author.bot:
        return
    if not message.guild:
        return

    row = await repository.get_channel(message.channel.id)
    if not row:
        return

    try:
        await message.author.ban(reason="Anti-raid: posted in marked channel")
        await repository.increment_ban_count(message.channel.id)
        await _update_warning_message(message.channel, row.ban_count + 1)
        embed = discord.Embed(
            description=f"Banned {message.author.mention} (anti-raid).",
            color=discord.Color.red(),
        )
        await message.channel.send(embed=embed, delete_after=5)
    except discord.Forbidden:
        embed = discord.Embed(
            description=f"Failed to ban {message.author.mention} — missing permissions.",
            color=discord.Color.yellow(),
        )
        await message.channel.send(embed=embed, delete_after=5)


async def _update_warning_message(channel: discord.TextChannel, ban_count: int) -> None:
    row = await repository.get_channel(channel.id)
    if not row or not row.message_id:
        return
    try:
        message = await channel.fetch_message(row.message_id)
        embed = message.embeds[0]
        embed.set_footer(text=f"Đã ban: {ban_count}")
        await message.edit(embed=embed)
    except (discord.NotFound, discord.HTTPException):
        pass
