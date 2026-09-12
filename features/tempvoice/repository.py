from sqlalchemy import select

from core.database import async_session
from features.tempvoice.models import CreateVoiceChannel, TempVoiceChannel


async def get_tempvoice(channel_id: int) -> TempVoiceChannel | None:
    async with async_session() as session:
        result = await session.execute(
            select(TempVoiceChannel).where(TempVoiceChannel.channel_id == channel_id)
        )
        return result.scalar_one_or_none()


async def get_all_tempvoice() -> list[TempVoiceChannel]:
    async with async_session() as session:
        result = await session.execute(
            select(TempVoiceChannel).order_by(TempVoiceChannel.created_at)
        )
        return list(result.scalars().all())



async def create_tempvoice(
    channel_id: int, guild_id: int, owner_id: int, panel_message_id: int | None = None
) -> None:
    async with async_session() as session:
        session.add(
            TempVoiceChannel(
                channel_id=channel_id,
                guild_id=guild_id,
                owner_id=owner_id,
                panel_message_id=panel_message_id,
            )
        )
        await session.commit()


async def delete_tempvoice(channel_id: int) -> TempVoiceChannel | None:
    async with async_session() as session:
        result = await session.execute(
            select(TempVoiceChannel).where(TempVoiceChannel.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if row:
            await session.delete(row)
            await session.commit()
        return row


async def set_tempvoice_panel(channel_id: int, panel_message_id: int | None) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(TempVoiceChannel).where(TempVoiceChannel.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.panel_message_id = panel_message_id
        await session.commit()


async def update_tempvoice_owner(channel_id: int, owner_id: int) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(TempVoiceChannel).where(TempVoiceChannel.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.owner_id = owner_id
        await session.commit()


async def get_createvoice(channel_id: int) -> CreateVoiceChannel | None:
    async with async_session() as session:
        result = await session.execute(
            select(CreateVoiceChannel).where(CreateVoiceChannel.channel_id == channel_id)
        )
        return result.scalar_one_or_none()


async def create_createvoice(channel_id: int, guild_id: int) -> None:
    async with async_session() as session:
        session.add(
            CreateVoiceChannel(
                channel_id=channel_id,
                guild_id=guild_id,
            )
        )
        await session.commit()


async def delete_createvoice(channel_id: int) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(CreateVoiceChannel).where(CreateVoiceChannel.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if row:
            await session.delete(row)
            await session.commit()
        return row

