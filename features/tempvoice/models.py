from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class TempVoiceChannel(Base):
    __tablename__ = "temp_voice_channels"
    __table_args__ = {"extend_existing": True}

    channel_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    panel_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
