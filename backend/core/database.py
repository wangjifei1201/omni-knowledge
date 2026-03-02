from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from core.config import get_settings

settings = get_settings()

# Engine configuration based on DB type
engine_kwargs = {
    "echo": settings.APP_DEBUG,
    "pool_size": 20,
    "max_overflow": 10,
    "pool_pre_ping": True,  # Enable connection health check
}

# MySQL 5.7 specific settings
if settings.DB_TYPE == "mysql":
    engine_kwargs["pool_recycle"] = 3600  # Recycle connections after 1 hour

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
