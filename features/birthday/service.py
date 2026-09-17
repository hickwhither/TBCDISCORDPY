import os
from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord

from features.birthday import repository
from features.connhen import service as connhen_service

TIMEZONE = os.environ.get("BIRTHDAY_TIMEZONE", "Asia/Ho_Chi_Minh")
GIFT_AMOUNT = int(os.environ.get("BIRTHDAY_GIFT_CONNHEN", "500"))
CELEBRATION_RETENTION_DAYS = 400


def _timezone() -> tzinfo:
    try:
        return ZoneInfo(TIMEZONE)
    except ZoneInfoNotFoundError:
        print(
            f"[birthday] WARNING: invalid timezone {TIMEZONE!r}. Falling back to UTC."
        )
        return timezone.utc


def today() -> date:
    return datetime.now(_timezone()).date()


def parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def matches_today(birth_date: date, day: date) -> bool:
    if birth_date.month != day.month:
        return False
    if birth_date.day == day.day:
        return True
    if (
        birth_date.month == 2
        and birth_date.day == 29
        and not is_leap_year(day.year)
        and day.day == 28
    ):
        return True
    return False


def age_on(birth_date: date, day: date) -> int:
    age = day.year - birth_date.year
    if (day.month, day.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def build_embed(
    birthday, member: discord.Member, day: date, gifted: bool
) -> discord.Embed:
    age = age_on(birthday.birth_date, day)
    embed = discord.Embed(
        title="🎂 Sinh nhật hôm nay!",
        description=f"Chúc mừng sinh nhật **{member.display_name}** {member.mention} 🎉",
        color=discord.Color.pink(),
    )
    embed.add_field(name="Tuổi mới", value=f"**{age}**", inline=True)
    if gifted:
        embed.add_field(
            name="Quà tặng connhen",
            value=connhen_service.format_amount(GIFT_AMOUNT),
            inline=True,
        )
    embed.set_footer(text=f"Sinh nhật ngày {birthday.birth_date.strftime('%d/%m')}")
    return embed


async def celebrate(
    bot: discord.Client,
    guild: discord.Guild,
    channel: discord.TextChannel,
    birthday,
    day: date,
) -> bool:
    member = guild.get_member(birthday.user_id)
    if not member:
        return False
    if await repository.was_celebrated(guild.id, member.id, day):
        return True

    gifted = GIFT_AMOUNT > 0 and birthday.last_gift_year != day.year

    try:
        await channel.send(embed=build_embed(birthday, member, day, gifted))
    except discord.Forbidden:
        return False
    except discord.HTTPException:
        return False

    if gifted:
        await connhen_service.add_connhen(member.id, GIFT_AMOUNT)
        await repository.set_last_gift_year(member.id, day.year)
    await repository.mark_celebrated(guild.id, member.id, day)
    return True


async def run_celebration_check(bot: discord.Client) -> None:
    day = today()
    birthdays = [
        b
        for b in await repository.get_all_birthdays()
        if matches_today(b.birth_date, day)
    ]

    for row in await repository.get_channels():
        guild = bot.get_guild(row.guild_id)
        if not guild:
            continue
        channel = guild.get_channel(row.channel_id)
        if not isinstance(channel, discord.TextChannel):
            continue
        for birthday in birthdays:
            await celebrate(bot, guild, channel, birthday, day)

    await repository.prune_celebrations(
        day - timedelta(days=CELEBRATION_RETENTION_DAYS)
    )
