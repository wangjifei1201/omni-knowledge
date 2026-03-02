from contextlib import asynccontextmanager

from api.routes import auth, chat, documents, retrieval, statistics, users
from core.config import get_settings
from core.database import Base, engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text

settings = get_settings()


def _sync_schema(connection):
    """Detect missing columns and add them via ALTER TABLE (development only)."""
    inspector = sa_inspect(connection)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue  # create_all will handle new tables
        existing_cols = {col["name"] for col in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing_cols:
                continue
            # Build column type DDL
            col_type = col.type.compile(dialect=connection.dialect)
            nullable = "NULL" if col.nullable else "NOT NULL"
            default_clause = ""
            if col.default is not None and col.default.is_scalar:
                val = col.default.arg
                if isinstance(val, str):
                    default_clause = f" DEFAULT '{val}'"
                else:
                    default_clause = f" DEFAULT {val}"
            ddl = f"ALTER TABLE `{table.name}` ADD COLUMN `{col.name}` {col_type} {nullable}{default_clause}"
            logger.info(f"Auto-adding missing column: {ddl}")
            connection.execute(text(ddl))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info(f"Starting {settings.APP_NAME}...")
    # Create tables (development only; use Alembic migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_sync_schema)
    logger.info("Database tables initialized")

    # Initialize services
    from services.rag.vector_store import faiss_vector_store
    from services.storage.local_storage import local_storage

    await faiss_vector_store.initialize()
    await local_storage.initialize()
    logger.info("Storage services initialized")

    # Create default admin account if not exists
    await create_default_admin()

    yield

    # Cleanup
    await engine.dispose()
    logger.info(f"{settings.APP_NAME} stopped")


async def create_default_admin():
    """Create default admin account if it doesn't exist"""
    from core.database import AsyncSessionLocal
    from core.security import get_password_hash
    from models.user import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        # Check if admin exists
        result = await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
        admin = result.scalar_one_or_none()

        if not admin:
            admin = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                display_name="系统管理员",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Default admin account created: {settings.ADMIN_USERNAME}")
        else:
            logger.info(f"Admin account already exists: {settings.ADMIN_USERNAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description="企业级智能知识库问答系统 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
api_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(documents.router, prefix=api_prefix)
app.include_router(chat.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(statistics.router, prefix=api_prefix)
app.include_router(retrieval.router, prefix=api_prefix)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "description": "企业级智能知识库问答系统",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
