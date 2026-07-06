import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.schemas.login_request import LoginRequest
from app.models.schemas.signup_request import SignupRequest
from app.models.schemas.refresh_token_request import RefreshTokenRequest

from app.repositories.user_repository import AsyncUserRepository
from passlib.context import CryptContext
from app.core.security import create_access_token, verify_token, verify_refresh_token
from app.api.dependencies import get_db

authentication_router = APIRouter(prefix="/auth")

crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@authentication_router.post("/login")
async def login(login_request: LoginRequest, db=Depends(get_db)):
    user_repo = AsyncUserRepository(db)
    user = await user_repo.get_user_by_username(login_request.username)
    if user is None or not crypt_context.verify(login_request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token, refresh_token = await create_access_token(data={"sub": str(user.id)}, db=db)
    return {"user_id": str(user.id), "access_token": access_token, "refresh_token": refresh_token}


@authentication_router.post("/signup")
async def signup(signup_request: SignupRequest, db=Depends(get_db)):
    user_repo = AsyncUserRepository(db)
    existing_email = await user_repo.get_user_by_email(signup_request.email)
    existing_username = await user_repo.get_user_by_username(signup_request.username)
    if existing_email or existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )
    hashed_password = crypt_context.hash(signup_request.password)
    new_user = await user_repo.create_user(
        email=signup_request.email,
        hashed_password=hashed_password,
        username=signup_request.username,
    )
    return {"message": "User created successfully", "user_id": new_user.id}


@authentication_router.post("/refresh")
async def refresh_token(refresh_token_request: RefreshTokenRequest, db=Depends(get_db)):
    result = await verify_refresh_token(refresh_token_request.refresh_token, db)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token, new_refresh_token = result
    return {"access_token": access_token, "refresh_token": new_refresh_token}