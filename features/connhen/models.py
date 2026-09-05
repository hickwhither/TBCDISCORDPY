from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class UserEconomy(Base):
    __tablename__ = "users_economy"
    __table_args__ = {"extend_existing": True}

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    connhen: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    last_daily: Mapped[Optional[datetime]] = mapped_column(nullable=True)