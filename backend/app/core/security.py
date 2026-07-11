from datetime import datetime, timedelta, timezone
import uuid

from jose import JWTError, jwt
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.refresh_token_repository import AsyncRefreshTokenRepository
from fastapi import status,HTTPException
settings = get_settings()

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


async def create_access_token(data: dict, db: AsyncSession):

    payload = data.copy()

    payload["exp"] = (
        datetime.now(timezone.utc)
        + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    access_token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    refresh_repo = AsyncRefreshTokenRepository(db)

    refresh_token_str = str(uuid.uuid4())

    expire_refresh = (
        datetime.now(timezone.utc)
        + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    

    db_refresh_token = await refresh_repo.create_token(
        int(data["sub"]),
        refresh_token_str,
        expire_refresh,
    )

    return access_token, db_refresh_token.token

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError as e:
 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token is invalid or expired") 

    

async def verify_refresh_token(
    token: str,
    db: AsyncSession,
):

    refresh_repo = AsyncRefreshTokenRepository(db)

    db_refresh_token = await refresh_repo.get_by_token(token)

    if db_refresh_token is None:
        return None

    if db_refresh_token.expire_at < datetime.now(timezone.utc):
        await refresh_repo.delete_token(token)
        return None

    await refresh_repo.delete_token(token)

    access_token, new_refresh_token = await create_access_token(
        {"sub": str(db_refresh_token.user_id)},
        db,
    )

    return access_token, new_refresh_token

async def delete_all_refresh_tokens_for_user(
    user_id: int,
    db: AsyncSession,
):

    refresh_repo = AsyncRefreshTokenRepository(db)

    await refresh_repo.delete_all_for_user(user_id)    