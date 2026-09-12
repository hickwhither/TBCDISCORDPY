from sqlalchemy import select

from core.database import async_session
from features.serverinfo.models import ServerInfoPanel


async def get_panel(guild_id: int) -> ServerInfoPanel | None:
    async with async_session() as session:
        result = await session.execute(
            select(ServerInfoPanel).where(ServerInfoPanel.guild_id == guild_id)
        )
        return result.scalar_one_or_none()


async def get_panels() -> list[ServerInfoPanel]:
    async with async_session() as session:
        result = await session.execute(
            select(ServerInfoPanel).order_by(ServerInfoPanel.created_at)
        )
        return list(result.scalars().all())


async def upsert_panel(guild_id: int, channel_id: int, message_id: int) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(ServerInfoPanel).where(ServerInfoPanel.guild_id == guild_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.channel_id = channel_id
            row.message_id = message_id
        else:
            session.add(
                ServerInfoPanel(
                    guild_id=guild_id,
                    channel_id=channel_id,
                    message_id=message_id,
                )
            )
        await session.commit()


async def remove_panel(guild_id: int) -> ServerInfoPanel | None:
    async with async_session() as session:
        result = await session.execute(
            select(ServerInfoPanel).where(ServerInfoPanel.guild_id == guild_id)
        )
        row = result.scalar_one_or_none()
        if row:
            await session.delete(row)
            await session.commit()
        return row
