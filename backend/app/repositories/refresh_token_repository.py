from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select, delete
from models import RefreshToken
from datetime import datetime

class AsyncRefreshTokenRepository:
    # 1. Inject an AsyncSession
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # 2. Use async def
    async def get_by_token(self, token_string: str):
        stmt = select(RefreshToken).where(RefreshToken.token == token_string)
        
        # 4. Await the execution
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_token(self, user_id: int, token_string: str, expire_at: datetime):
        new_token = RefreshToken(
            user_id=user_id, 
            token=token_string, 
            expire_at=expire_at
        )
        self.db.add(new_token)
        
        # 5. Await the commit and refresh
        await self.db.commit()
        await self.db.refresh(new_token)
        return new_token
    
    async def delete_token(self, token_string: str):
        stmt = select(RefreshToken).where(RefreshToken.token == token_string)
        result = await self.db.execute(stmt)
        token = result.scalars().first()
        
        if token:
            await self.db.delete(token)
            await self.db.commit()
            return True
        return False
    

    # Add this to your AsyncRefreshTokenRepository class
    async def delete_all_for_user(self, user_id: int):
        """Deletes all refresh tokens for a specific user (Global Logout)."""
        stmt = delete(RefreshToken).where(RefreshToken.user_id == user_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True
    
    # Add this to your AsyncRefreshTokenRepository class
    async def delete_expired_tokens(self):
        stmt = delete(RefreshToken).where(RefreshToken.expire_at < datetime.utcnow())
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.rowcount