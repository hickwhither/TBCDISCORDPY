import asyncio
import re

import discord


async def reply_ephemeral(
    interaction: discord.Interaction, content: str, *, delay: float = 5, **kwargs
) -> None:
    try:
        msg = await interaction.followup.send(content, **kwargs)
    except discord.NotFound, discord.HTTPException:
        return
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except discord.NotFound, discord.HTTPException:
        pass


async def resolve_member(guild: discord.Guild, value: str) -> discord.Member | None:
    value = value.strip()
    if not value:
        return None

    match = re.fullmatch(r"<@!?(\d+)>", value)
    if match:
        user_id = int(match.group(1))
    elif value.isdigit():
        user_id = int(value)
    else:
        user_id = None

    if user_id:
        member = guild.get_member(user_id)
        if member:
            return member
        try:
            return await guild.fetch_member(user_id)
        except discord.NotFound, discord.HTTPException:
            return None

    search = value.casefold()
    exact, prefix = [], []
    for m in guild.members:
        names = {m.name, m.display_name, m.global_name or "", m.nick or ""}
        folded = {c.casefold() for c in names if c}
        if search in folded:
            exact.append(m)
        elif any(c.startswith(search) for c in folded):
            prefix.append(m)

    if len(exact) == 1:
        return exact[0]
    if not exact and len(prefix) == 1:
        return prefix[0]
    return None
