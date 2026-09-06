from datetime import datetime

from sqlalchemy import select

from core.database import async_session
from features.tickets.models import Ticket, TicketPanelSetup


async def get_by_channel(channel_id: int) -> Ticket | None:
    async with async_session() as session:
        result = await session.execute(
            select(Ticket).where(Ticket.channel_id == channel_id)
        )
        return result.scalar_one_or_none()


async def list_open_by_owner(guild_id: int, owner_id: int) -> list[Ticket]:
    async with async_session() as session:
        result = await session.execute(
            select(Ticket)
            .where(
                Ticket.guild_id == guild_id,
                Ticket.owner_id == owner_id,
                Ticket.status == "open",
            )
            .order_by(Ticket.created_at)
        )
        return list(result.scalars().all())


async def get_all_open() -> list[Ticket]:
    async with async_session() as session:
        result = await session.execute(
            select(Ticket).where(Ticket.status == "open").order_by(Ticket.created_at)
        )
        return list(result.scalars().all())


async def get_all() -> list[Ticket]:
    async with async_session() as session:
        result = await session.execute(select(Ticket).order_by(Ticket.created_at))
        return list(result.scalars().all())


async def add(
    channel_id: int,
    guild_id: int,
    owner_id: int,
    panel_message_id: int | None = None,
) -> None:
    async with async_session() as session:
        session.add(
            Ticket(
                channel_id=channel_id,
                guild_id=guild_id,
                owner_id=owner_id,
                panel_message_id=panel_message_id,
                last_activity_at=datetime.now().astimezone().replace(tzinfo=None),
            )
        )
        await session.commit()


async def remove(channel_id: int) -> Ticket | None:
    async with async_session() as session:
        result = await session.execute(
            select(Ticket).where(Ticket.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if row:
            await session.delete(row)
            await session.commit()
        return row


async def set_status(channel_id: int, status: str) -> Ticket | None:
    async with async_session() as session:
        result = await session.execute(
            select(Ticket).where(Ticket.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        row.status = status
        await session.commit()
        return row


async def update_activity(channel_id: int) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(Ticket).where(Ticket.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.last_activity_at = datetime.now().astimezone().replace(tzinfo=None)
        await session.commit()


async def set_warned(channel_id: int) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(Ticket).where(Ticket.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.warned_at = datetime.now().astimezone().replace(tzinfo=None)
        await session.commit()


async def add_panel(
    channel_id: int, guild_id: int, message_id: int, category_id: int | None
) -> None:
    async with async_session() as session:
        session.add(
            TicketPanelSetup(
                channel_id=channel_id,
                guild_id=guild_id,
                message_id=message_id,
                category_id=category_id,
            )
        )
        await session.commit()


async def get_panel(channel_id: int) -> TicketPanelSetup | None:
    async with async_session() as session:
        result = await session.execute(
            select(TicketPanelSetup).where(TicketPanelSetup.channel_id == channel_id)
        )
        return result.scalar_one_or_none()


async def get_panels() -> list[TicketPanelSetup]:
    async with async_session() as session:
        result = await session.execute(select(TicketPanelSetup))
        return list(result.scalars().all())


async def remove_panel(channel_id: int) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(TicketPanelSetup).where(TicketPanelSetup.channel_id == channel_id)
        )
        row = result.scalar_one_or_none()
        if row:
            await session.delete(row)
            await session.commit()
