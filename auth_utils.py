"""
Authentication Utilities - JWT validation and user verification
"""

import os
import jwt
from typing import Optional, Dict, Any
from functools import wraps
from fastapi import Request, HTTPException
import logging

logger = logging.getLogger(__name__)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

if not SUPABASE_JWT_SECRET:
    raise ValueError("SUPABASE_JWT_SECRET must be set")


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token from Supabase Auth
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error verifying JWT token: {str(e)}")
        return None


def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        User ID (UUID) or None if invalid
    """
    payload = verify_jwt_token(token)
    if payload:
        return payload.get("sub")  # 'sub' claim contains user ID
    return None


def require_auth(func):
    """
    Decorator to require authentication for endpoint
    Validates JWT token and adds user_id to request.state
    
    Usage:
        @app.post("/api/search")
        @require_auth
        async def search_endpoint(request: Request):
            user_id = request.state.user_id
            # ... rest of endpoint logic
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Missing Authorization header"
            )
        
        # Verify token
        payload = verify_jwt_token(auth_header)
        
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )
        
        # Extract user ID
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload"
            )
        
        # Add user_id to request state
        request.state.user_id = user_id
        request.state.user_email = payload.get("email")
        request.state.user_role = payload.get("role", "user")
        
        # Call the actual endpoint function
        return await func(request, *args, **kwargs)
    
    return wrapper


def optional_auth(func):
    """
    Decorator for optional authentication
    Adds user_id to request.state if token is present and valid
    Does not raise error if token is missing
    
    Usage:
        @app.get("/api/public-data")
        @optional_auth
        async def public_endpoint(request: Request):
            user_id = getattr(request.state, 'user_id', None)
            # ... return data (personalized if user_id exists)
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        
        if auth_header:
            payload = verify_jwt_token(auth_header)
            if payload:
                request.state.user_id = payload.get("sub")
                request.state.user_email = payload.get("email")
                request.state.user_role = payload.get("role", "user")
        
        return await func(request, *args, **kwargs)
    
    return wrapper


def get_user_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get user information from request state
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dict with user information or None
    """
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        return None
    
    return {
        "user_id": user_id,
        "email": getattr(request.state, "user_email", None),
        "role": getattr(request.state, "user_role", "user")
    }


async def extract_user_from_token(authorization: Optional[str]) -> str:
    """
    Extract and validate user ID from authorization token
    
    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")
        
    Returns:
        User ID (UUID)
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )
    
    user_id = get_user_id_from_token(authorization)
    
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
    
    return user_id


async def get_optional_user_from_token(authorization: Optional[str]) -> Optional[str]:
    """
    Extract user ID from token if present (optional authentication)
    
    Args:
        authorization: Authorization header value (optional)
        
    Returns:
        User ID (UUID) or None if token missing/invalid
    """
    if not authorization:
        return None
    
    return get_user_id_from_token(authorization)
