from datetime import date

from sqlalchemy import delete, select

from core.database import async_session
from features.birthday.models import Birthday, BirthdayCelebration, BirthdayChannel


async def get_birthday(user_id: int) -> Birthday | None:
    async with async_session() as session:
        result = await session.execute(
            select(Birthday).where(Birthday.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def get_all_birthdays() -> list[Birthday]:
    async with async_session() as session:
        result = await session.execute(select(Birthday))
        return list(result.scalars().all())


async def set_birthday(user_id: int, birth_date: date) -> Birthday:
    async with async_session() as session:
        row = await get_birthday(user_id)
        if row:
            row.birth_date = birth_date
            row.last_gift_year = None
        else:
            row = Birthday(user_id=user_id, birth_date=birth_date)
            session.add(row)
        await session.commit()
        return row


async def set_last_gift_year(user_id: int, year: int) -> None:
    async with async_session() as session:
        row = await get_birthday(user_id)
        if row:
            row.last_gift_year = year
            await session.commit()


async def remove_birthday(user_id: int) -> Birthday | None:
    async with async_session() as session:
        row = await get_birthday(user_id)
        if row:
            await session.delete(row)
            await session.commit()
        return row


async def get_channel(guild_id: int) -> BirthdayChannel | None:
    async with async_session() as session:
        result = await session.execute(
            select(BirthdayChannel).where(BirthdayChannel.guild_id == guild_id)
        )
        return result.scalar_one_or_none()


async def get_channels() -> list[BirthdayChannel]:
    async with async_session() as session:
        result = await session.execute(select(BirthdayChannel))
        return list(result.scalars().all())


async def set_channel(guild_id: int, channel_id: int) -> None:
    async with async_session() as session:
        row = await get_channel(guild_id)
        if row:
            row.channel_id = channel_id
        else:
            session.add(BirthdayChannel(guild_id=guild_id, channel_id=channel_id))
        await session.commit()


async def remove_channel(guild_id: int) -> BirthdayChannel | None:
    async with async_session() as session:
        row = await get_channel(guild_id)
        if row:
            await session.delete(row)
            await session.commit()
        return row


async def was_celebrated(guild_id: int, user_id: int, day: date) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(BirthdayCelebration).where(
                BirthdayCelebration.guild_id == guild_id,
                BirthdayCelebration.user_id == user_id,
                BirthdayCelebration.celebrated_on == day,
            )
        )
        return result.scalar_one_or_none() is not None


async def mark_celebrated(guild_id: int, user_id: int, day: date) -> None:
    async with async_session() as session:
        session.add(
            BirthdayCelebration(
                guild_id=guild_id,
                user_id=user_id,
                celebrated_on=day,
            )
        )
        await session.commit()


async def prune_celebrations(before: date) -> None:
    async with async_session() as session:
        await session.execute(
            delete(BirthdayCelebration).where(
                BirthdayCelebration.celebrated_on < before
            )
        )
        await session.commit()
