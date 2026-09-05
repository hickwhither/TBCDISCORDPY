from datetime import datetime

from sqlalchemy import select

from core.database import async_session

from .models import UserEconomy


async def get_or_create(user_id: int) -> UserEconomy:
    async with async_session() as session:
        result = await session.execute(
            select(UserEconomy).where(UserEconomy.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row:
            return row
        row = UserEconomy(user_id=user_id, connhen=0)
        session.add(row)
        await session.commit()
        return row


async def add_connhen(user_id: int, amount: int) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(UserEconomy).where(UserEconomy.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            row = UserEconomy(user_id=user_id, connhen=0)
            session.add(row)
        row.connhen += amount
        await session.commit()
        return row.connhen


async def sub_connhen(user_id: int, amount: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(UserEconomy).where(UserEconomy.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if not row or row.connhen < amount:
            return False
        row.connhen -= amount
        await session.commit()
        return True


async def set_last_daily(user_id: int, when: datetime) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(UserEconomy).where(UserEconomy.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            row = UserEconomy(user_id=user_id, connhen=0)
            session.add(row)
        row.last_daily = when
        await session.commit()
