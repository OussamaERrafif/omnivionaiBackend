"""
Subscription and quota checking middleware for FastAPI
Handles search limit enforcement and Supabase integration
"""

import os
from typing import Optional, Dict, Any
from supabase import create_client, Client
from fastapi import HTTPException, Header

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

supabase: Optional[Client] = None

# ✅ SECURITY FIX: Removed sensitive credential logging
print("\n" + "="*70)
print("🔧 SUPABASE SUBSCRIPTION MIDDLEWARE INITIALIZATION")
print("="*70)
print(f"📍 SUPABASE_URL: {'✅ Configured' if SUPABASE_URL else '❌ Not configured'}")
print(f"🔑 SUPABASE_SERVICE_ROLE_KEY: {'✅ Configured' if SUPABASE_SERVICE_ROLE_KEY else '❌ Not configured'}")

if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print("✅ SUCCESS: Supabase client initialized for subscription management")
        print("   Quota checking: ENABLED")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize Supabase client")
        print(f"   Error type: {type(e).__name__}")
        # Only show detailed error in development
        if os.getenv("ENV") == "development":
            print(f"   Error details: {str(e)}")
        supabase = None
else:
    print("⚠️  WARNING: Supabase credentials incomplete - quota checking DISABLED")
    print("   Add these to your .env file:")
    print("   SUPABASE_URL=https://your-project.supabase.co")
    print("   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here")
    print("   Running in DEVELOPMENT MODE (all searches allowed)")
    
print("="*70 + "\n")


async def check_user_quota(authorization: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if user has available search quota
    
    Args:
        authorization: Bearer token from request header
        
    Returns:
        Dict containing quota information
        
    Raises:
        HTTPException: If quota is exceeded or validation fails
    """
    # If Supabase is not configured, allow all searches (development mode)
    if not supabase:
        return {
            "can_search": True,
            "searches_remaining": 999,
            "plan_type": "free",
            "message": "Quota checking disabled (dev mode)"
        }
    
    # Extract user from authorization token
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            # Verify JWT and get user
            user_response = supabase.auth.get_user(token)
            if user_response and hasattr(user_response, 'user'):
                user_id = user_response.user.id
        except Exception as e:
            print(f"⚠️ Failed to verify user token: {e}")
    
    # If no user (anonymous), allow limited searches
    if not user_id:
        return {
            "can_search": True,
            "searches_remaining": 1,
            "plan_type": "anonymous",
            "message": "Anonymous user - limited access"
        }
    
    try:
        # Call database function to check quota
        response = supabase.rpc('check_search_quota', {'p_user_id': user_id}).execute()
        
        if response.data and len(response.data) > 0:
            quota_info = response.data[0]
            
            # If quota exceeded, raise HTTP error
            if not quota_info.get('can_search', False):
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Search quota exceeded",
                        "message": "You've reached your monthly search limit. Upgrade to Pro for unlimited searches.",
                        "quota": {
                            "plan_type": quota_info.get('plan_type', 'free'),
                            "searches_remaining": quota_info.get('searches_remaining', 0),
                            "reset_date": quota_info.get('reset_date', ''),
                        }
                    }
                )
            
            return quota_info
        else:
            # No subscription found, allow search (will be created on increment)
            return {
                "can_search": True,
                "searches_remaining": 3,
                "plan_type": "free",
                "message": "New user"
            }
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        print(f"⚠️ Error checking quota: {e}")
        # On error, allow search (fail open)
        return {
            "can_search": True,
            "searches_remaining": 3,
            "plan_type": "free",
            "message": "Quota check failed - allowing search"
        }


async def increment_user_search(
    search_id: str,
    query_preview: str,
    authorization: Optional[str] = None
) -> Dict[str, Any]:
    """
    Increment user's search count after successful search
    
    Args:
        search_id: Unique identifier for the search
        query_preview: Preview of the search query (first 100 chars)
        authorization: Bearer token from request header
        
    Returns:
        Dict containing updated quota information
    """
    # If Supabase is not configured, skip increment (development mode)
    if not supabase:
        return {
            "success": True,
            "searches_used": 0,
            "searches_remaining": 999,
            "message": "Development mode"
        }
    
    # Extract user from authorization token
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            user_response = supabase.auth.get_user(token)
            if user_response and hasattr(user_response, 'user'):
                user_id = user_response.user.id
        except Exception as e:
            print(f"⚠️ Failed to verify user token: {e}")
    
    # If no user, skip increment
    if not user_id:
        return {
            "success": True,
            "searches_used": 0,
            "searches_remaining": 0,
            "message": "Anonymous user"
        }
    
    try:
        # Call database function to increment count
        response = supabase.rpc('increment_search_count', {
            'p_user_id': user_id,
            'p_search_id': search_id,
            'p_query_preview': query_preview[:100] if query_preview else None
        }).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            return {
                "success": False,
                "searches_used": 0,
                "searches_remaining": 0,
                "message": "Failed to increment"
            }
            
    except Exception as e:
        print(f"⚠️ Error incrementing search count: {e}")
        return {
            "success": False,
            "searches_used": 0,
            "searches_remaining": 0,
            "message": str(e)
        }


def get_quota_headers(quota_info: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate HTTP headers with quota information
    
    Args:
        quota_info: Quota information dictionary
        
    Returns:
        Dict of HTTP headers
    """
    return {
        "X-Search-Limit": str(quota_info.get("searches_remaining", 0)),
        "X-Plan-Type": quota_info.get("plan_type", "free"),
        "X-Reset-Date": quota_info.get("reset_date", ""),
    }
