import discord

from core import config

COLOR_CREATE = discord.Color.green()
COLOR_UPDATE = discord.Color.gold()
COLOR_DELETE = discord.Color.red()
COLOR_INFO = discord.Color.blurple()
COLOR_JOIN = discord.Color.green()
COLOR_LEAVE = discord.Color.orange()


def _channel(bot: discord.Client) -> discord.TextChannel | None:
    if not getattr(config, "LOG_CHANNEL_ID", 0):
        return None
    channel = bot.get_channel(config.LOG_CHANNEL_ID)
    return channel if isinstance(channel, discord.TextChannel) else None


def _footer(
    embed: discord.Embed, reason: str | None = None, by: str | None = None
) -> None:
    parts = []
    if by:
        parts.append(f"Bởi: {by}")
    if reason:
        parts.append(f"Lý do: {reason}")
    embed.set_footer(text=" • ".join(parts))
    embed.timestamp = discord.utils.utcnow()


def _user_name(author: discord.abc.User | discord.Member) -> str:
    return str(author)


async def send(
    bot: discord.Client,
    embed: discord.Embed,
    reason: str | None = None,
    by: str | None = None,
) -> None:
    channel = _channel(bot)
    if not channel:
        return
    _footer(embed, reason=reason, by=by)
    try:
        await channel.send(embed=embed)
    except discord.Forbidden, discord.HTTPException:
        pass


# ---------------------------------------------------------------- member update


async def log_nickname_change(bot, before, after) -> None:
    old = before.nick or "(không có)"
    new = after.nick or "(không có)"
    if old == new:
        return
    embed = discord.Embed(title="✏️ Nickname Changed", color=COLOR_UPDATE)
    embed.description = f"{after.mention} ({before})"
    embed.add_field(name="Nick cũ", value=old, inline=True)
    embed.add_field(name="Nick mới", value=new, inline=True)
    await send(bot, embed)


async def log_username_change(bot, before, after) -> None:
    if str(before) == str(after):
        return
    embed = discord.Embed(title="✏️ Username Changed", color=COLOR_UPDATE)
    embed.description = f"{after.mention} ({before.id})"
    embed.add_field(name="Tên cũ", value=str(before), inline=True)
    embed.add_field(name="Tên mới", value=str(after), inline=True)
    await send(bot, embed)


async def log_avatar_change(bot, before, after) -> None:
    if (before.display_avatar.url if before.display_avatar else None) == (
        after.display_avatar.url if after.display_avatar else None
    ):
        return
    embed = discord.Embed(title="🖼️ Avatar Changed", color=COLOR_UPDATE)
    embed.description = f"{after.mention} ({after})"
    embed.set_thumbnail(url=after.display_avatar.url)
    await send(bot, embed)


async def log_role_change(bot, before, after) -> None:
    removed = [r for r in before.roles if r not in after.roles]
    added = [r for r in after.roles if r not in before.roles]
    if not added and not removed:
        return
    embed = discord.Embed(title="🛡️ Roles Updated", color=COLOR_UPDATE)
    embed.description = f"{after.mention} ({after})"
    if added:
        embed.add_field(
            name="Thêm role", value=", ".join(r.mention for r in added), inline=False
        )
    if removed:
        embed.add_field(
            name="Gỡ role", value=", ".join(r.mention for r in removed), inline=False
        )
    await send(bot, embed)


async def log_boost_change(bot, before, after) -> None:
    if before.premium_since == after.premium_since:
        return
    embed = discord.Embed(title="💎 Booster", color=COLOR_UPDATE)
    embed.description = f"{after.mention} ({after})"
    embed.add_field(name="Boost từ", value=str(before.premium_since), inline=True)
    embed.add_field(name="Boost tới", value=str(after.premium_since), inline=True)
    await send(bot, embed)


# ---------------------------------------------------------------- message events


async def log_message_delete(bot, message: discord.Message) -> None:
    if not message.guild or message.author.bot:
        return
    embed = discord.Embed(title="🗑️ Message Deleted", color=COLOR_DELETE)
    embed.description = f"{message.author.mention} ({_user_name(message.author)})"
    embed.add_field(name="Kênh", value=message.channel.mention, inline=True)
    content = message.content or "(nội dung trống)"
    embed.add_field(name="Tin nhắn bị xóa", value=content[:1000] or "…", inline=False)
    if message.attachments:
        embed.add_field(
            name="Attachment",
            value="\n".join(a.filename for a in message.attachments),
            inline=False,
        )
    await send(bot, embed)
    for attachment in message.attachments:
        try:
            await _channel(bot).send(
                f"🗑️ Attachment bị xóa bởi {message.author.mention} ({message.channel.mention}): {attachment.url}"
            )
        except discord.Forbidden, discord.HTTPException:
            pass


async def log_message_edit(
    bot, before: discord.Message, after: discord.Message
) -> None:
    if not before.guild or before.author.bot:
        return
    if before.content == after.content:
        return
    embed = discord.Embed(title="📝 Message Edited", color=COLOR_UPDATE)
    embed.description = f"{before.author.mention} ({_user_name(before.author)}) in {before.channel.mention}"
    embed.add_field(
        name="Trước", value=(before.content or "(trống)")[:1000], inline=False
    )
    embed.add_field(name="Sau", value=(after.content or "(trống)")[:1000], inline=False)
    embed.add_field(
        name="Jump", value=f"[Nhảy tới tin]({after.jump_url})", inline=False
    )
    await send(bot, embed)


async def log_bulk_delete(bot, messages) -> None:
    singles = [m for m in messages if m.channel and m.author and not m.author.bot]
    if not singles:
        return
    channel = singles[0].channel
    embed = discord.Embed(title="🗑️ Bulk Delete", color=COLOR_DELETE)
    embed.description = f"**{len(singles)}** tin nhắn bị xóa trong {channel.mention}"
    lines = []
    for m in singles[:10]:
        snippet = (m.content or "(không có nội dung)").replace("\n", " ")
        lines.append(f"**{_user_name(m.author)}**: {snippet[:200]}")
    embed.add_field(name="Nội dung", value="\n".join(lines)[:1024], inline=False)
    await send(bot, embed)


# ---------------------------------------------------------------- member lifecycle


async def log_member_join(bot, member: discord.Member) -> None:
    embed = discord.Embed(title="📥 Member Joined", color=COLOR_JOIN)
    embed.description = f"{member.mention} ({_user_name(member)})"
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(
        name="Tài khoản tạo",
        value=discord.utils.format_dt(member.created_at, style="R"),
        inline=True,
    )
    await send(bot, embed)


async def log_member_remove(bot, member: discord.Member) -> None:
    embed = discord.Embed(title="📤 Member Left", color=COLOR_LEAVE)
    embed.description = f"{member.mention} ({_user_name(member)})"
    roles = ", ".join(r.mention for r in member.roles if r != member.guild.default_role)
    embed.add_field(name="Roles lúc rời", value=roles or "(không có)", inline=False)
    await send(bot, embed)


# ---------------------------------------------------------------- ban / kick / timeout


async def log_member_ban(bot, guild: discord.Guild, user: discord.User) -> None:
    embed = discord.Embed(title="🔨 Member Banned", color=COLOR_DELETE)
    embed.description = f"{user.mention} ({_user_name(user)})"
    embed.add_field(name="ID", value=user.id, inline=True)
    await send(bot, embed)


async def log_member_unban(bot, guild: discord.Guild, user: discord.User) -> None:
    embed = discord.Embed(title="🔓 Member Unbanned", color=COLOR_CREATE)
    embed.description = f"{user.mention} ({_user_name(user)})"
    embed.add_field(name="ID", value=user.id, inline=True)
    await send(bot, embed)


# ---------------------------------------------------------------- audit entries (kick/timeout)


async def log_audit_entry(bot, entry: discord.AuditLogEntry) -> None:
    action = entry.action
    target = entry.target
    reason = entry.reason
    by = _user_name(entry.user) if entry.user else None

    if action == discord.AuditLogAction.kick and isinstance(target, discord.User):
        embed = discord.Embed(title="👢 Member Kicked", color=COLOR_DELETE)
        embed.description = f"{target.mention} ({_user_name(target)})"
        await send(bot, embed, reason=reason, by=by)

    elif action == discord.AuditLogAction.ban and isinstance(target, discord.User):
        embed = discord.Embed(title="🔨 Member Banned", color=COLOR_DELETE)
        embed.description = f"{target.mention} ({_user_name(target)})"
        await send(bot, embed, reason=reason, by=by)

    elif action == discord.AuditLogAction.unban and isinstance(target, discord.User):
        embed = discord.Embed(title="🔓 Member Unbanned", color=COLOR_CREATE)
        embed.description = f"{target.mention} ({_user_name(target)})"
        await send(bot, embed, reason=reason, by=by)

    elif action == discord.AuditLogAction.member_update and isinstance(
        target, discord.User
    ):
        embed = discord.Embed(title="⏱️ Member Timed Out", color=COLOR_UPDATE)
        embed.description = f"{target.mention} ({_user_name(target)})"
        await send(bot, embed, reason=reason, by=by)


# ---------------------------------------------------------------- channel / role


async def log_channel_create(bot, channel: discord.abc.GuildChannel) -> None:
    embed = discord.Embed(title="🆕 Channel Created", color=COLOR_CREATE)
    embed.description = f"{channel.mention} ({channel.name})"
    embed.add_field(name="Loại", value=str(channel.type), inline=True)
    await send(bot, embed)


async def log_channel_delete(bot, channel: discord.abc.GuildChannel) -> None:
    embed = discord.Embed(title="🚮 Channel Deleted", color=COLOR_DELETE)
    embed.description = f"**{channel.name}**"
    embed.add_field(name="Loại", value=str(channel.type), inline=True)
    embed.add_field(name="ID", value=channel.id, inline=True)
    await send(bot, embed)


async def log_channel_update(
    bot, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
) -> None:
    if before.name != after.name:
        embed = discord.Embed(title="🛠️ Channel Renamed", color=COLOR_UPDATE)
        embed.description = f"{after.mention}"
        embed.add_field(name="Tên cũ", value=before.name, inline=True)
        embed.add_field(name="Tên mới", value=after.name, inline=True)
        await send(bot, embed)


async def log_role_create(bot, role: discord.Role) -> None:
    embed = discord.Embed(title="🆕 Role Created", color=COLOR_CREATE)
    embed.description = f"{role.mention} ({role.name})"
    await send(bot, embed)


async def log_role_delete(bot, role: discord.Role) -> None:
    embed = discord.Embed(title="🚮 Role Deleted", color=COLOR_DELETE)
    embed.description = f"**{role.name}**"
    embed.add_field(name="ID", value=role.id, inline=True)
    await send(bot, embed)


async def log_role_update(bot, before: discord.Role, after: discord.Role) -> None:
    if before.name != after.name:
        embed = discord.Embed(title="🛠️ Role Renamed", color=COLOR_UPDATE)
        embed.description = f"{after.mention}"
        embed.add_field(name="Tên cũ", value=before.name, inline=True)
        embed.add_field(name="Tên mới", value=after.name, inline=True)
        await send(bot, embed)


# ---------------------------------------------------------------- guild


async def log_guild_update(bot, before: discord.Guild, after: discord.Guild) -> None:
    changed = []
    if before.name != after.name:
        changed.append(f"**Tên server**: {before.name} → {after.name}")
    if before.icon != after.icon:
        changed.append("**Icon** đã thay đổi")
    if before.banner != after.banner:
        changed.append("**Banner** đã thay đổi")
    if before.afk_channel != after.afk_channel:
        changed.append("**AFK channel** đã thay đổi")
    if not changed:
        return
    embed = discord.Embed(title="🛠️ Server Updated", color=COLOR_UPDATE)
    embed.description = "\n".join(changed)
    await send(bot, embed)
