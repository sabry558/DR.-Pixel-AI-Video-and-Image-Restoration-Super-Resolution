from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models.database.user import User


class AsyncUserRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ==========================================
    # 1. AUTHENTICATION / READ METHODS
    # ==========================================

    async def get_user_by_email(self, email: str) -> User | None:
        """Used for Login and checking if an email is already registered."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalars().first()
    async def get_user_by_username(self, username: str) -> User | None:
        """Used for Login and checking if a username is already registered."""
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalars().first()
    async def get_user_by_id(self, user_id: int) -> User | None:
        """Used to fetch the current logged-in user's profile data."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # ==========================================
    # 2. CREATE (SIGNUP)
    # ==========================================

    async def create_user(self, email: str, hashed_password: str, username: str) -> User:
        """Creates a new user. MUST receive a hashed password, never plain text!"""
        new_user = User(
            email=email,
            password=hashed_password,
            username=username
        )
        self.db.add(new_user)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(new_user)
        return new_user

    # ==========================================
    # 3. UPDATE METHODS
    # ==========================================

    ALLOWED_UPDATE_FIELDS = {"username", "email"}

    async def update_user(self, user_id: int, update_data: dict) -> User | None:
        """
        Updates specific fields for a user (e.g., changing username or email).
        Only whitelisted fields are applied, to prevent mass-assignment
        of sensitive columns like hashed_password or is_admin.
        """
        safe_data = {k: v for k, v in update_data.items() if k in self.ALLOWED_UPDATE_FIELDS}
        if not safe_data:
            return await self.get_by_id(user_id)

        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**safe_data)
            .execution_options(synchronize_session="fetch")
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return await self.get_by_id(user_id)

    # ==========================================
    # 4. DELETE & ADMIN METHODS
    # ==========================================

    async def delete_user(self, user_id: int) -> bool:
        """Deletes a user account entirely."""
        stmt = delete(User).where(User.id == user_id)
        try:
            result = await self.db.execute(stmt)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        # Returns True if a row was actually deleted, False if user didn't exist
        return result.rowcount > 0

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Used for Admin dashboards to list users with pagination."""
        stmt = select(User).order_by(User.id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())