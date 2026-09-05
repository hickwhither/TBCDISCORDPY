import os
import warnings
from sqlalchemy import exc as sa_exc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "tbc.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

warnings.filterwarnings(
    "ignore",
    message="This declarative base already contains a class with the same class name and module name.*",
    category=sa_exc.SAWarning,
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
