from sqlalchemy import select
from core.database import async_session
from features.tempvoice.models import TempVoiceChannel


async def get_by_channel(channel_id: int) -> TempVoiceChannel | None:
    async with async_session() as session:
        result = await session.execute(
            select(TempVoiceChannel).where(TempVoiceChannel.channel_id == channel_id)
        )
        return result.scalar_one_or_none()


async def get_all() -> list[TempVoiceChannel]:
    async with async_session() as session:
        result = await session.execute(
            select(TempVoiceChannel).order_by(TempVoiceChannel.created_at)
        )
        return list(result.scalars().all())


async def add(channel_id: int, guild_id: int, owner_id: int, panel_message_id: int | None = None) -> None:
    async with async_session() as session:
        session.add(TempVoiceChannel(
            channel_id=channel_id,
            guild_id=guild_id,
            owner_id=owner_id,
            panel_message_id=panel_message_id,
        ))
        await session.commit()


async def remove(channel_id: int) -> TempVoiceChannel | None:
    async with async_session() as session:
        result = await session.execute(
            select(TempVoiceChannel).where(TempVoiceChannel.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if row:
            await session.delete(row)
            await session.commit()
        return row


async def set_owner(channel_id: int, owner_id: int) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(TempVoiceChannel).where(TempVoiceChannel.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.owner_id = owner_id
        await session.commit()