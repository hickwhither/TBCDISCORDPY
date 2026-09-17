from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Birthday(Base):
    __tablename__ = "birthdays"
    __table_args__ = {"extend_existing": True}

    user_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_gift_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class BirthdayChannel(Base):
    __tablename__ = "birthday_channels"
    __table_args__ = {"extend_existing": True}

    guild_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class BirthdayCelebration(Base):
    __tablename__ = "birthday_celebrations"
    __table_args__ = {"extend_existing": True}

    guild_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    celebrated_on: Mapped[date] = mapped_column(
        Date, primary_key=True, autoincrement=False
    )
