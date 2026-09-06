from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = {"extend_existing": True}

    channel_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="open", index=True
    )
    panel_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(server_default=func.now())
    warned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class TicketPanelSetup(Base):
    __tablename__ = "ticket_panel_setup"
    __table_args__ = {"extend_existing": True}

    channel_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
