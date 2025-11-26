from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from config import settings
from models import User, UserRole
import secrets
import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)  # Make it optional for API token support


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security), db = Depends(lambda: __import__('database').get_database())) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user_doc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return User(**user_doc)


def get_current_user():
    return get_current_user_dependency


def require_role(required_roles: list[UserRole]):
    async def role_checker(credentials: HTTPAuthorizationCredentials = Depends(security), db = Depends(lambda: __import__('database').get_database())) -> User:
        user = await get_current_user_dependency(credentials, db)
        if user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return role_checker


def generate_api_token() -> str:
    """Generate a secure API token"""
    return secrets.token_urlsafe(32)


def hash_api_token(token: str) -> str:
    """Hash API token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()


async def get_current_user_from_api_token(
    x_api_token: Optional[str] = Header(None),
    db = Depends(lambda: __import__('database').get_database())
) -> User:
    """Authenticate user via API token"""
    if not x_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API token required",
            headers={"WWW-Authenticate": "ApiToken"}
        )
    
    # Hash the provided token
    token_hash = hash_api_token(x_api_token)
    
    # Find token in database
    token_doc = await db.api_tokens.find_one({
        "token_hash": token_hash,
        "is_active": True
    }, {"_id": 0})
    
    if not token_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API token"
        )
    
    # Get user
    user_doc = await db.users.find_one({"id": token_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return User(**user_doc)


async def get_current_user_flexible(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_token: Optional[str] = Header(None),
    db = Depends(lambda: __import__('database').get_database())
) -> User:
    """Authenticate user via JWT or API token"""
    # Try API token first
    if x_api_token:
        return await get_current_user_from_api_token(x_api_token, db)
    
    # Fall back to JWT
    if credentials:
        return await get_current_user_dependency(credentials, db)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (JWT or API token)",
        headers={"WWW-Authenticate": "Bearer"}
    )
