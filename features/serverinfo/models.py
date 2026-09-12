from datetime import datetime

from sqlalchemy import BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ServerInfoPanel(Base):
    __tablename__ = "server_info_panels"
    __table_args__ = {"extend_existing": True}

    guild_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
