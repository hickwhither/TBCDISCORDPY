import os
import pathlib
import sqlite3
import warnings
from datetime import datetime

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


def _sqlite_path(url: str) -> str | None:
    if not url.startswith("sqlite"):
        return None
    path = url.rsplit("///", 1)[-1]
    if path in ("", "memory"):
        return None
    return path


def _prune_backups(backup_dir: pathlib.Path, keep: int = 15) -> None:
    backups = sorted(backup_dir.glob("tbc-*.db"), reverse=True)
    for old in backups[keep:]:
        old.unlink(missing_ok=True)


def backup_db() -> None:
    path = _sqlite_path(DATABASE_URL)
    if path is None or not os.path.exists(path):
        return

    backup_dir = pathlib.Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backup_dir / f"tbc-{stamp}.db"

    src = sqlite3.connect(path)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    _prune_backups(backup_dir, keep=15)
    print(f"[Backup] Database -> {dest}")


async def init_db() -> None:
    _ensure_sqlite_dir(DATABASE_URL)
    import asyncio
    from alembic import command
    from alembic.config import Config

    await asyncio.to_thread(backup_db)

    def upgrade() -> None:
        cfg = Config("alembic.ini")
        cfg.set_main_option("script_location", "migrations")
        command.upgrade(cfg, "head")

    await asyncio.to_thread(upgrade)