import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], default="pbkdf2_sha256")


# EXPORTED FUNCTIONS
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "iss": "ai-data-analyst"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], issuer="ai-data-analyst")
    except JWTError as e:
        logger.error(f"JWT decode failed: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})


security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    if not credentials:
        raise HTTPException(401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, detail="Invalid token")

    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if not user:
            raise HTTPException(401, detail="User not found")
        role = user.role if hasattr(user, "role") and user.role else "Viewer"
        return {
            "id": user.id,
            "email": user.email,
            "role": role,
            "full_name": user.full_name,
            "is_active": user.is_active,
        }


async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    return current_user


async def get_current_superuser(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(403, detail="Insufficient permissions")
    return current_user
