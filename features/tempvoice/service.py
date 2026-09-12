import os

import discord

from features.tempvoice import repository
from features.tempvoice.views import OWNER_PERMS, ControlPanelView, build_embed

TRIGGER_NAME = os.environ.get("TEMP_VOICE_TRIGGER", "Create Voice")
ROOM_TEMPLATE = os.environ.get("TEMP_VOICE_ROOM_TEMPLATE", "{name}'s Room")


def is_trigger_channel(channel) -> bool:
    return isinstance(channel, discord.VoiceChannel) and channel.name == TRIGGER_NAME


async def create_room(
    bot, member: discord.Member, trigger: discord.VoiceChannel
) -> None:
    guild = member.guild
    base = ROOM_TEMPLATE.format(name=member.display_name or "User")[:95]
    name = await _unique_room_name(guild, base)

    channel = await guild.create_voice_channel(
        name=name,
        category=trigger.category,
        reason=f"TempVoice: tạo phòng cho {member}",
    )
    await repository.create_tempvoice(channel.id, guild.id, member.id, None)
    try:
        await channel.set_permissions(
            member, overwrite=OWNER_PERMS, reason="TempVoice: cấp quyền chủ phòng"
        )
        await member.move_to(channel, reason="TempVoice: đưa vào phòng mới")
    except discord.Forbidden:
        await channel.delete()
        raise

    embed = build_embed(guild, channel, member)
    view = ControlPanelView(bot, channel.id)
    try:
        panel = await channel.send(embed=embed, view=view)
        await repository.set_tempvoice_panel(channel.id, panel.id)
    except (discord.Forbidden, discord.HTTPException) as exc:
        print(f"[tempvoice] không gửi được control panel: {exc!r}")


async def delete_room(channel: discord.VoiceChannel) -> None:
    try:
        await channel.delete()
    except discord.NotFound, discord.HTTPException:
        pass
    except discord.Forbidden as exc:
        print(f"[tempvoice] không xóa được phòng {channel.id}: {exc!r}")
        return
    try:
        await repository.delete_tempvoice(channel.id)
    except Exception as exc:
        print(f"[tempvoice] lỗi xóa row {channel.id}: {exc!r}")


async def _unique_room_name(guild: discord.Guild, base: str) -> str:
    taken = {c.name for c in guild.voice_channels}
    if base not in taken:
        return base
    index = 2
    while f"{base} ({index})" in taken:
        index += 1
    return f"{base} ({index})"
