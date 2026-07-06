from app.db.session import engine
from app.db.base import Base
from app.models.database import user, job, refresh_token

async def init_db():
    print(Base.metadata.tables.keys())   # <-- add this

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)