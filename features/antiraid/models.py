from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class MarkedChannel(Base):
    __tablename__ = "marked_channels"

    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    marked_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ban_count: Mapped[int] = mapped_column(server_default="0", default=0)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())