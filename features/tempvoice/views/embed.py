import discord

from features.tempvoice import repository
from features.tempvoice.views.config import THUMBNAIL_URL

_MISSING = discord.utils.MISSING


def build_embed(
    guild: discord.Guild, channel: discord.VoiceChannel, owner: discord.Member
) -> discord.Embed:
    everyone = channel.overwrites_for(guild.default_role)
    locked = everyone.connect is False
    hidden = everyone.view_channel is False
    limit = channel.user_limit if channel.user_limit else "Không giới hạn"

    embed = discord.Embed(
        title=f"🎙 {channel.name}",
        description="Chọn lệnh bên dưới để điều khiển phòng của bạn.",
        color=discord.Color.blurple(),
    )
    embed.add_field(name="👑 Chủ phòng", value=owner.mention, inline=True)
    embed.add_field(name="👥 Trong phòng", value=str(len(channel.members)), inline=True)
    embed.add_field(name="👤 Giới hạn", value=str(limit), inline=True)
    embed.add_field(name="🔒 Khóa", value="Bật" if locked else "Tắt", inline=True)
    embed.add_field(name="👁 Ẩn", value="Bật" if hidden else "Tắt", inline=True)
    if THUMBNAIL_URL:
        embed.set_thumbnail(url=THUMBNAIL_URL)
    embed.set_footer(text=f"ID phòng: {channel.id}")
    return embed


async def refresh_panel(channel: discord.VoiceChannel) -> None:
    row = await repository.get_tempvoice(channel.id)
    await edit_panel(channel.guild, channel, row)


async def edit_panel(
    guild: discord.Guild,
    channel: discord.VoiceChannel,
    row,
    view=_MISSING,
) -> None:
    if not row or not row.panel_message_id:
        return
    owner = guild.get_member(row.owner_id)
    if not owner:
        return
    try:
        message = await channel.fetch_message(row.panel_message_id)
        await message.edit(embed=build_embed(guild, channel, owner), view=view)
    except (discord.NotFound, discord.HTTPException):
        pass
