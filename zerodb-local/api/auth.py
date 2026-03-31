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


# Cached cloud user (avoids re-validating on every request)
_cached_cloud_user: Optional[User] = None
_cached_api_key: Optional[str] = None


async def verify_cloud_credentials(token: str = None, api_key: str = None) -> Optional[dict]:
    """
    Verify credentials with AINative cloud API.
    Supports both JWT Bearer tokens and API keys.
    """
    try:
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        elif token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            return None

        async with httpx.AsyncClient() as client:
            # Try /api/v1/public/auth/me first (supports both auth methods)
            for path in ["/api/v1/public/auth/me", "/auth/me"]:
                try:
                    response = await client.get(
                        f"{CLOUD_API_URL}{path}",
                        headers=headers,
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        return response.json()
                except Exception:
                    continue
        return None
    except Exception as e:
        print(f"Error verifying cloud credentials: {e}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user.

    Cloud mode (default): Validates against AINative cloud API using:
      1. CLOUD_API_KEY env var (auto-auth, no headers needed)
      2. X-API-Key header
      3. Authorization: Bearer <jwt> header

    Local mode: Returns mock user for offline development.
    Set ZERODB_AUTH_MODE=local for offline dev.
    """
    global _cached_cloud_user, _cached_api_key

    # Local-only mode (offline development)
    if AUTH_MODE == "local":
        return User(
            id=os.getenv("ZERODB_USER_ID", "00000000-0000-0000-0000-000000000001"),
            email=os.getenv("ZERODB_USER_EMAIL", "dev@localhost"),
            username=os.getenv("ZERODB_USERNAME", "local-developer")
        )

    # Cloud mode — try multiple auth sources

    # 1. Check CLOUD_API_KEY env var (auto-auth for local-to-cloud sync)
    env_api_key = os.getenv("CLOUD_API_KEY", "")
    if env_api_key and len(env_api_key) > 10:
        # Cache to avoid re-validating every request
        if _cached_cloud_user and _cached_api_key == env_api_key:
            return _cached_cloud_user

        user_data = await verify_cloud_credentials(api_key=env_api_key)
        if user_data:
            _cached_api_key = env_api_key
            _cached_cloud_user = User(
                id=user_data.get("id", ""),
                email=user_data.get("email", ""),
                username=user_data.get("username", user_data.get("email", "").split("@")[0]),
                is_active=user_data.get("is_active", True)
            )
            print(f"✅ Cloud auth: {_cached_cloud_user.email} (ID: {_cached_cloud_user.id})")
            return _cached_cloud_user

    # 2. Check Bearer token from request header
    if credentials and credentials.credentials:
        token = credentials.credentials
        # Short tokens are API keys, long ones are JWTs
        if len(token) < 100:
            user_data = await verify_cloud_credentials(api_key=token)
        else:
            user_data = await verify_cloud_credentials(token=token)

        if user_data:
            return User(
                id=user_data.get("id", ""),
                email=user_data.get("email", ""),
                username=user_data.get("username", user_data.get("email", "").split("@")[0]),
                is_active=user_data.get("is_active", True)
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Set CLOUD_API_KEY env var or pass Authorization header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Alias for compatibility
get_user = get_current_user


# Alias matching cloud backend's dependency name (used by all routers)
async def get_current_user_flexible(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Flexible auth compatible with cloud backend's get_current_user_flexible.
    All zerodb-local routers use this as their auth dependency.
    """
    return await get_current_user(credentials=credentials, db=db)
