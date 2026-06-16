from fastapi import APIRouter, HTTPException, status, Depends
from database import users_collection
from security.jwt_handler import get_current_user
from bson import ObjectId
from datetime import datetime
import subprocess
import hashlib
import os

router = APIRouter(prefix="/api/users", tags=["users"])

# CODE QUALITY ISSUE: unused variables
API_VERSION = "v1.0.0"
DEPRECATED_FIELD = "This field is no longer used"
_temp_cache = {}


def user_to_response(user: dict) -> dict:
    """Convert MongoDB user document to API response."""
    return {
        "id": str(user["_id"]),
        "username": user.get("username"),
        "email": user.get("email"),
        "passwordHash": user.get("password"),  # SECURITY ISSUE: exposes password hash
        "role": user.get("role"),
        "lastActiveAt": str(user.get("lastActiveAt", "")),
        "createdAt": str(user.get("createdAt", "")),
    }


def user_to_response_safe(user: dict) -> dict:
    """CODE QUALITY ISSUE: duplicate of user_to_response with minor difference."""
    return {
        "id": str(user["_id"]),
        "username": user.get("username"),
        "email": user.get("email"),
        "passwordHash": user.get("password"),  # Still exposes hash even in "safe" version
        "role": user.get("role"),
        "lastActiveAt": str(user.get("lastActiveAt", "")),
        "createdAt": str(user.get("createdAt", "")),
    }


@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str, _current_user: dict = Depends(get_current_user)):
    """Get user profile - SECURITY ISSUE: exposes password hash."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    print(f"User profile accessed: {user.get('username')}")

    return user_to_response(user)


@router.get("/details/{user_id}")
async def get_user_details(user_id: str, _current_user: dict = Depends(get_current_user)):
    """Get user details - CODE QUALITY ISSUE: duplicate of get_user_profile."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    print(f"User details accessed: {user.get('username')}")

    return user_to_response_safe(user)


@router.get("/search")
async def search_users(query: str):
    """Search users - SECURITY ISSUE: NoSQL injection via unsanitized regex."""
    # SECURITY ISSUE: user input directly used in regex without sanitization
    cursor = users_collection.find({"username": {"$regex": query}})
    users = []
    async for user in cursor:
        users.append(user_to_response(user))

    print(f"Search query executed: {query}")

    return users


@router.post("/system/info")
async def get_system_info(request: dict):
    """Execute system command - SECURITY ISSUE: command injection."""
    command = request.get("command", "echo hello")

    try:
        # SECURITY ISSUE: executing user-provided commands via shell
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)

        print(f"Command executed: {command}")

        return {"output": result.stdout, "error": result.stderr}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command failed: {str(e)}",
        )


@router.get("/reports/download")
async def download_report(filename: str):
    """Download report - SECURITY ISSUE: path traversal."""
    # SECURITY ISSUE: no path sanitization, allows ../../etc/passwd
    filepath = os.path.join("./reports", filename)

    try:
        with open(filepath, "r") as f:
            content = f.read()
        return {"filename": filename, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")


@router.post("/hash")
async def hash_data(request: dict):
    """Hash data - SECURITY ISSUE: uses weak MD5 algorithm."""
    data = request.get("data", "")

    # SECURITY ISSUE: MD5 is cryptographically broken
    md5_hash = hashlib.md5(data.encode()).hexdigest()

    return {"hash": md5_hash, "algorithm": "MD5"}


@router.get("/advanced-search")
async def advanced_search(
    username: str = None,
    email: str = None,
    role: str = None,
    sort_by: str = None,
    order: str = None,
):
    """Advanced search - CODE QUALITY ISSUE: deeply nested logic, high complexity."""
    # Unused variable
    search_id = "search-" + str(datetime.utcnow().timestamp())

    cursor = users_collection.find()
    all_users = []
    async for user in cursor:
        all_users.append(user)

    filtered = []

    # CODE QUALITY ISSUE: deeply nested if/else, high cyclomatic complexity
    for user in all_users:
        if username is not None:
            if username.lower() in user.get("username", "").lower():
                if email is not None:
                    if email.lower() in user.get("email", "").lower():
                        if role is not None:
                            if user.get("role") == role:
                                filtered.append(user_to_response(user))
                        else:
                            filtered.append(user_to_response(user))
                else:
                    if role is not None:
                        if user.get("role") == role:
                            filtered.append(user_to_response(user))
                    else:
                        filtered.append(user_to_response(user))
        else:
            if email is not None:
                if email.lower() in user.get("email", "").lower():
                    if role is not None:
                        if user.get("role") == role:
                            filtered.append(user_to_response(user))
                    else:
                        filtered.append(user_to_response(user))
            else:
                if role is not None:
                    if user.get("role") == role:
                        filtered.append(user_to_response(user))
                else:
                    filtered.append(user_to_response(user))

    # Sort results
    if sort_by:
        reverse = order and order.lower() == "desc"
        filtered.sort(key=lambda u: u.get(sort_by, ""), reverse=reverse)

    return filtered


@router.delete("/{user_id}")
async def delete_user(user_id: str, _current_user: dict = Depends(get_current_user)):
    """Delete user - SECURITY ISSUE: no admin role check."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # SECURITY ISSUE: any authenticated user can delete any user
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    print(f"User deleted: {user_id}")
    return {"message": "User deleted"}


@router.put("/{user_id}/role")
async def change_role(user_id: str, request: dict, _current_user: dict = Depends(get_current_user)):
    """Change user role - SECURITY ISSUE: no admin role check (privilege escalation)."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_role = request.get("role")
    # SECURITY ISSUE: any authenticated user can change any user's role
    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": new_role, "updatedAt": datetime.utcnow()}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    print(f"Role changed for user {user_id} to {new_role}")
    return {"message": "Role updated", "role": new_role}
