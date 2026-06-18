"""JWT creation/decoding and FastAPI authentication dependencies."""
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from config import settings
from database import users_collection

security = HTTPBearer(auto_error=False)

SECRET_KEY = settings.server_secret
ALGORITHM = "HS256"
EXPIRATION_HOURS = settings.jwt_expiration_hours


def create_token(user_id: str, username: str, role: str) -> str:
    """Create a signed JWT for the given user."""
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=EXPIRATION_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT, raising 401 if invalid or expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Resolve the authenticated user from the bearer token, or raise 401."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user["_id"] = str(user["_id"])
    return user
