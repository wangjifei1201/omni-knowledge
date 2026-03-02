from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "omni-knowledge"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # Database Type: "postgresql" or "mysql"
    DB_TYPE: Literal["postgresql", "mysql"] = "mysql"

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "omni_knowledge"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "omni_knowledge"
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_CHARSET: str = "utf8mb4"

    @property
    def DATABASE_URL(self) -> str:
        """Async database URL"""
        if self.DB_TYPE == "mysql":
            return (
                f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
                f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
                f"?charset={self.MYSQL_CHARSET}"
            )
        else:
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Sync database URL for migrations"""
        if self.DB_TYPE == "mysql":
            return (
                f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
                f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
                f"?charset={self.MYSQL_CHARSET}"
            )
        else:
            return (
                f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # FAISS Vector Store (Local)
    FAISS_INDEX_PATH: str = "./data/faiss_index"

    # Local File Storage (replaces MinIO)
    LOCAL_STORAGE_PATH: str = "./data/storage"

    # LLM
    LLM_API_BASE: str = "http://localhost:8080/v1"
    LLM_API_KEY: str = "your-llm-api-key"
    LLM_MODEL_NAME: str = "qwen2.5-72b-instruct"

    # Embedding
    EMBEDDING_API_BASE: str = "http://localhost:8081/v1"
    EMBEDDING_API_KEY: str = "your-embedding-api-key"
    EMBEDDING_MODEL_NAME: str = "bge-large-zh-v1.5"
    EMBEDDING_DIMENSION: int = 1024

    # Reranker
    RERANKER_API_BASE: str = "http://localhost:8082/v1"
    RERANKER_MODEL_NAME: str = "bge-reranker-large"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Default Admin Account
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_EMAIL: str = "admin@example.com"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
