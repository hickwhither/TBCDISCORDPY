import os
import pathlib
import warnings

from dotenv import load_dotenv
from sqlalchemy import exc as sa_exc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///data/tbc.db",
)

warnings.filterwarnings(
    "ignore",
    message="This declarative base already contains a class with the same class name and module name.*",
    category=sa_exc.SAWarning,
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite"):
        db_path = url.rsplit("///", 1)[-1]
        if db_path and db_path != "memory":
            pathlib.Path(os.path.dirname(db_path) or ".").mkdir(parents=True, exist_ok=True)


async def init_db() -> None:
    _ensure_sqlite_dir(DATABASE_URL)
    import asyncio
    from alembic import command
    from alembic.config import Config

    def upgrade() -> None:
        cfg = Config("alembic.ini")
        cfg.set_main_option("script_location", "migrations")
        command.upgrade(cfg, "head")

    await asyncio.to_thread(upgrade)