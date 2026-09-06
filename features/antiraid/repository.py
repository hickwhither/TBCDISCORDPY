from sqlalchemy import select

from core.database import async_session
from features.antiraid.models import MarkedChannel


async def get_channel(channel_id: int) -> MarkedChannel | None:
    async with async_session() as session:
        result = await session.execute(
            select(MarkedChannel).where(MarkedChannel.channel_id == channel_id)
        )
        return result.scalar_one_or_none()


async def get_all() -> list[MarkedChannel]:
    async with async_session() as session:
        result = await session.execute(select(MarkedChannel))
        return list(result.scalars().all())


async def add_channel(
    channel_id: int, guild_id: int, marked_by: int, message_id: int
) -> None:
    async with async_session() as session:
        session.add(
            MarkedChannel(
                channel_id=channel_id,
                guild_id=guild_id,
                marked_by=marked_by,
                message_id=message_id,
            )
        )
        await session.commit()


async def remove_channel(channel_id: int) -> MarkedChannel | None:
    async with async_session() as session:
        result = await session.execute(
            select(MarkedChannel).where(MarkedChannel.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if row:
            await session.delete(row)
            await session.commit()
        return row


async def increment_ban_count(channel_id: int) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(MarkedChannel).where(MarkedChannel.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.ban_count += 1
        await session.commit()
