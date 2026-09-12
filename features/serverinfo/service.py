import time

import discord

from features.serverinfo import repository

_refresh_cooldown: dict[int, float] = {}
_REFRESH_DEBOUNCE_SEC = 3.0


def _should_refresh(guild_id: int) -> bool:
    now = time.monotonic()
    last = _refresh_cooldown.get(guild_id, 0.0)
    if now - last < _REFRESH_DEBOUNCE_SEC:
        return False
    _refresh_cooldown[guild_id] = now
    return True


def build_embed(guild: discord.Guild) -> discord.Embed:
    owner_text = guild.owner.mention if guild.owner else "Không truy xuất được"
    created = guild.created_at.strftime("%d/%m/%Y")
    icon_url = guild.icon.url if guild.icon else None

    humans = sum(1 for m in guild.members if not m.bot)
    total_text = len(guild.text_channels)
    total_voice = len(guild.voice_channels)
    total_categories = len(guild.categories)

    verified_role = discord.utils.get(guild.roles, name="verified")
    if verified_role:
        verified_role_text = f"{len(verified_role.members)} người"
    else:
        verified_role_text = "Không có role 'verified'"

    embed = discord.Embed(
        title=f"📊 Thông Tin Server: {guild.name}",
        color=discord.Color.blurple(),
    )
    if icon_url:
        embed.set_thumbnail(url=icon_url)

    embed.add_field(name="🆔 ID", value=str(guild.id), inline=True)
    embed.add_field(name="👑 Owner", value=owner_text, inline=True)
    embed.add_field(name="📅 Ngày tạo", value=created, inline=True)

    embed.add_field(
        name="👥 Thành viên",
        value=f"Tổng: **{guild.member_count}**\n"
        f"Không bot: **{humans}**\n"
        f"Bot: **{max(0, (guild.member_count or 0) - humans)}**",
        inline=True,
    )
    embed.add_field(
        name="💬 Kênh",
        value=f"Text: **{total_text}**\n"
        f"Voice: **{total_voice}**\n"
        f"Category: **{total_categories}**",
        inline=True,
    )
    embed.add_field(
        name="🎭 Khác",
        value=f"Roles: **{len(guild.roles)}**\nEmoji: **{len(guild.emojis)}**",
        inline=True,
    )

    embed.add_field(
        name="⭐ Boosts",
        value=f"Level: **{guild.premium_tier}**\n"
        f"Số boost: **{guild.premium_subscription_count}**",
        inline=True,
    )
    embed.add_field(
        name="🛡️ Role 'verified'",
        value=verified_role_text,
        inline=True,
    )

    return embed


async def post_panel(
    channel: discord.TextChannel, guild: discord.Guild
) -> discord.Message | None:
    embed = build_embed(guild)
    try:
        message = await channel.send(embed=embed)
    except discord.Forbidden, discord.HTTPException:
        return None
    await repository.upsert_panel(guild.id, channel.id, message.id)
    return message


async def refresh_panel(guild: discord.Guild) -> None:
    if not _should_refresh(guild.id):
        return
    row = await repository.get_panel(guild.id)
    if not row:
        return
    channel = guild.get_channel(row.channel_id)
    if not isinstance(channel, discord.TextChannel):
        return
    embed = build_embed(guild)
    try:
        message = await channel.fetch_message(row.message_id)
        await message.edit(embed=embed)
    except discord.NotFound, discord.Forbidden, discord.HTTPException:
        try:
            message = await channel.send(embed=embed)
            await repository.upsert_panel(guild.id, channel.id, message.id)
        except discord.Forbidden, discord.HTTPException:
            pass
