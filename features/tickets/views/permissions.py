import discord

from features.tickets.views.config import STAFF_ROLE_NAME

BOT_PERMS = discord.PermissionOverwrite(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    attach_files=True,
    embed_links=True,
    add_reactions=True,
    manage_messages=True,
    manage_channels=True,
)

OWNER_PERMS = discord.PermissionOverwrite(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    attach_files=True,
    embed_links=True,
    add_reactions=True,
)


def owner_overwrite(*, send: bool) -> discord.PermissionOverwrite:
    return discord.PermissionOverwrite(
        view_channel=True,
        send_messages=send,
        read_message_history=True,
        attach_files=True,
        embed_links=True,
        add_reactions=True,
    )


GUEST_PERMS = discord.PermissionOverwrite(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    attach_files=True,
    embed_links=True,
    add_reactions=True,
)

STAFF_PERMS = discord.PermissionOverwrite(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    attach_files=True,
    embed_links=True,
    add_reactions=True,
    manage_messages=True,
    manage_channels=True,
)


def is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(
        role.name.casefold() == STAFF_ROLE_NAME.casefold() for role in member.roles
    )


async def staff_overwrites(guild: discord.Guild) -> dict:
    overlords = [
        r
        for r in guild.roles
        if r.name.casefold() == STAFF_ROLE_NAME.casefold()
        or r.permissions.administrator
    ]
    manageable = {r for r in overlords if r.is_assignable()}
    return {role: STAFF_PERMS for role in manageable}
