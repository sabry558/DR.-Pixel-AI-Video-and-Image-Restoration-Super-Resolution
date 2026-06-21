from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import settings

# 1. Define your connection string
def _postgresql_url(url: str) -> str:
    if url.startswith("postgresql+psycopg2://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url
# 2. Create the Engine
engine = create_engine(
    _postgresql_url(settings.database_url),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)