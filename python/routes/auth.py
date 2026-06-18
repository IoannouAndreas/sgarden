"""Authentication routes: registration and login."""
from datetime import datetime
import bcrypt
from fastapi import APIRouter, HTTPException, status
from models.user import RegisterRequest, LoginRequest, AuthResponse
from database import users_collection
from security.jwt_handler import create_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Register a new user and return an auth token."""
    # Check if username exists
    existing_user = await users_collection.find_one({"username": request.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Check if email exists
    existing_email = await users_collection.find_one({"email": request.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    # Create user
    user_doc = {
        "username": request.username,
        "email": request.email,
        "password": hash_password(request.password),
        "role": "user",
        "lastActiveAt": datetime.utcnow(),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await users_collection.insert_one(user_doc)
    user_id = str(result.inserted_id)

    token = create_token(user_id, request.username, "user")
    print(f"User registered: {request.username}")
    return AuthResponse(token=token, username=request.username, role="user")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Authenticate a user and return an auth token."""
    user = await users_collection.find_one({"username": request.username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not verify_password(request.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Update last active
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"lastActiveAt": datetime.utcnow()}},
    )

    user_id = str(user["_id"])
    token = create_token(user_id, user["username"], user["role"])
    print(f"User logged in: {user['username']}")
    return AuthResponse(token=token, username=user["username"], role=user["role"])
