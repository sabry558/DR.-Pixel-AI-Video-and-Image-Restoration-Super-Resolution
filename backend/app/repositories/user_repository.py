from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from models import User

class AsyncUserRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ==========================================
    # 1. AUTHENTICATION / READ METHODS
    # ==========================================
    
    async def get_by_email(self, email: str):
        """Used for Login and checking if an email is already registered."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, user_id: int):
        """Used to fetch the current logged-in user's profile data."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # ==========================================
    # 2. CREATE (SIGNUP)
    # ==========================================

    async def create_user(self, email: str, hashed_password: str, username: str = None):
        """Creates a new user. MUST receive a hashed password, never plain text!"""
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            username=username
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    # ==========================================
    # 3. UPDATE METHODS
    # ==========================================

    async def update_user(self, user_id: int, update_data: dict):
        """
        Updates specific fields for a user (e.g., changing username or password).
        Accepts a dictionary of fields to update.
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
            .execution_options(synchronize_session="fetch")
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        # Return the updated user
        return await self.get_by_id(user_id)

    # ==========================================
    # 4. DELETE & ADMIN METHODS
    # ==========================================

    async def delete_user(self, user_id: int):
        """Deletes a user account entirely."""
        stmt = delete(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        # Returns True if a row was actually deleted, False if user didn't exist
        return result.rowcount > 0

    async def get_all_users(self, skip: int = 0, limit: int = 100):
        """Used for Admin dashboards to list users with pagination."""
        stmt = select(User).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()