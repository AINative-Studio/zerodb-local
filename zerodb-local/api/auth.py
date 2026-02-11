"""
Authentication Module for ZeroLocal
Integrates with AINative cloud authentication system
"""
import os
import httpx
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db


class User(BaseModel):
    """User model from AINative platform"""
    id: str
    email: str
    username: str = Field(default="")
    is_active: bool = Field(default=True)

    class Config:
        from_attributes = True


# Security scheme
security = HTTPBearer(auto_error=False)

# Environment configuration
CLOUD_API_URL = os.getenv("CLOUD_API_URL", "https://api.ainative.studio")
AUTH_MODE = os.getenv("ZERODB_AUTH_MODE", "cloud")  # "cloud" or "local"


async def verify_cloud_token(token: str) -> Optional[dict]:
    """
    Verify JWT token with AINative cloud API

    Args:
        token: JWT token from Authorization header

    Returns:
        dict: User data from cloud API or None if invalid
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CLOUD_API_URL}/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0
            )

            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        print(f"Error verifying cloud token: {e}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user

    Supports two modes:
    1. Cloud mode (default): Validates JWT tokens with AINative cloud API
    2. Local mode: Returns local user for offline development

    Set ZERODB_AUTH_MODE=local for offline development

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        User: Authenticated user object

    Raises:
        HTTPException: If authentication fails in cloud mode
    """
    # Local-only mode (offline development)
    if AUTH_MODE == "local":
        return User(
            id="local-user",
            email=os.getenv("ZERODB_USER_EMAIL", "dev@localhost"),
            username=os.getenv("ZERODB_USERNAME", "local-developer")
        )

    # Cloud mode - validate with AINative API
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials. Please login at https://ainative.studio",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token with cloud API
    user_data = await verify_cloud_token(credentials.credentials)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login at https://ainative.studio",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Return authenticated user from cloud API
    return User(
        id=user_data.get("id", ""),
        email=user_data.get("email", ""),
        username=user_data.get("username", user_data.get("email", "").split("@")[0]),
        is_active=user_data.get("is_active", True)
    )


# Alias for compatibility
get_user = get_current_user
