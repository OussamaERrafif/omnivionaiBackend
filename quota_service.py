"""
Quota Service - Atomic quota management with database-backed operations
Handles all quota checking, decrementing, and refunding operations
"""

import os
from typing import Dict, Any, Optional
from supabase import create_client, Client
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client with service role (bypasses RLS)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


class QuotaExceededError(Exception):
    """Raised when user has exceeded their search quota"""
    def __init__(self, message: str, remaining: int = 0, plan_type: str = "free"):
        self.message = message
        self.remaining = remaining
        self.plan_type = plan_type
        super().__init__(self.message)


class QuotaService:
    """Service for managing user search quotas"""
    
    @staticmethod
    async def get_quota_status(user_id: str) -> Dict[str, Any]:
        """
        Get current quota status for a user
        
        Args:
            user_id: User UUID
            
        Returns:
            Dict with quota information
        """
        try:
            result = supabase.table("user_subscriptions").select(
                "searches_remaining, searches_limit, plan_type, subscription_status"
            ).eq("user_id", user_id).single().execute()
            
            if not result.data:
                # User doesn't have subscription record, create default
                logger.info(f"Creating default subscription for user {user_id}")
                return await QuotaService._create_default_subscription(user_id)
            
            data = result.data
            return {
                "searches_remaining": data["searches_remaining"],
                "searches_limit": data["searches_limit"],
                "plan_type": data["plan_type"],
                "subscription_status": data["subscription_status"],
                "has_quota": data["searches_remaining"] > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting quota status for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    async def _create_default_subscription(user_id: str) -> Dict[str, Any]:
        """Create default free subscription for new user"""
        default_data = {
            "user_id": user_id,
            "plan_type": "free",
            "searches_remaining": 10,
            "searches_limit": 10,
            "subscription_status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            result = supabase.table("user_subscriptions").insert(default_data).execute()
            
            return {
                "searches_remaining": 10,
                "searches_limit": 10,
                "plan_type": "free",
                "subscription_status": "active",
                "has_quota": True
            }
        except Exception as e:
            logger.error(f"Error creating default subscription: {str(e)}")
            raise
    
    @staticmethod
    async def check_and_decrement_quota(user_id: str) -> Dict[str, Any]:
        """
        Atomically check if user has quota and decrement it
        Uses database function for atomicity (prevents race conditions)
        
        Args:
            user_id: User UUID
            
        Returns:
            Dict with updated quota information
            
        Raises:
            QuotaExceededError: If user has no remaining searches
        """
        try:
            # Call database function for atomic operation
            result = supabase.rpc(
                "decrement_search_quota",
                {"user_uuid": user_id}
            ).execute()
            
            if not result.data:
                # Check current status to provide detailed error
                status = await QuotaService.get_quota_status(user_id)
                raise QuotaExceededError(
                    f"Search quota exceeded. You have {status['searches_remaining']} of {status['searches_limit']} searches remaining.",
                    remaining=status['searches_remaining'],
                    plan_type=status['plan_type']
                )
            
            data = result.data
            logger.info(f"Quota decremented for user {user_id}. Remaining: {data['searches_remaining']}")
            
            return {
                "searches_remaining": data["searches_remaining"],
                "searches_limit": data["searches_limit"],
                "plan_type": data["plan_type"],
                "decremented": True
            }
            
        except QuotaExceededError:
            raise
        except Exception as e:
            logger.error(f"Error decrementing quota for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    async def refund_quota(user_id: str, reason: str = "search_failed") -> Dict[str, Any]:
        """
        Refund a search quota to the user (called on search failure)
        
        Args:
            user_id: User UUID
            reason: Reason for refund
            
        Returns:
            Dict with updated quota information
        """
        try:
            # Call database function for atomic refund
            result = supabase.rpc(
                "refund_search_quota",
                {"user_uuid": user_id}
            ).execute()
            
            if result.data:
                data = result.data
                logger.info(f"Quota refunded for user {user_id}. Reason: {reason}. New remaining: {data['searches_remaining']}")
                
                return {
                    "searches_remaining": data["searches_remaining"],
                    "searches_limit": data["searches_limit"],
                    "refunded": True,
                    "reason": reason
                }
            else:
                logger.warning(f"Could not refund quota for user {user_id}")
                return {"refunded": False, "reason": "no_subscription_found"}
            
        except Exception as e:
            logger.error(f"Error refunding quota for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    async def update_subscription(
        user_id: str,
        plan_type: str,
        searches_limit: int,
        subscription_status: str = "active"
    ) -> Dict[str, Any]:
        """
        Update user subscription (called by webhook handler)
        
        Args:
            user_id: User UUID
            plan_type: Plan type (free, pro, enterprise)
            searches_limit: New search limit
            subscription_status: Subscription status
            
        Returns:
            Dict with updated subscription information
        """
        try:
            update_data = {
                "plan_type": plan_type,
                "searches_limit": searches_limit,
                "searches_remaining": searches_limit,  # Reset remaining on plan change
                "subscription_status": subscription_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = supabase.table("user_subscriptions").update(
                update_data
            ).eq("user_id", user_id).execute()
            
            if not result.data:
                # If no record exists, create one
                insert_data = {
                    **update_data,
                    "user_id": user_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                result = supabase.table("user_subscriptions").insert(insert_data).execute()
            
            logger.info(f"Subscription updated for user {user_id}: {plan_type} with {searches_limit} searches")
            
            return {
                "plan_type": plan_type,
                "searches_remaining": searches_limit,
                "searches_limit": searches_limit,
                "subscription_status": subscription_status,
                "updated": True
            }
            
        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id}: {str(e)}")
            raise


# Convenience functions for direct import
async def get_quota_status(user_id: str) -> Dict[str, Any]:
    """Get quota status for a user"""
    return await QuotaService.get_quota_status(user_id)


async def check_and_decrement_quota(user_id: str) -> Dict[str, Any]:
    """Check and decrement quota atomically"""
    return await QuotaService.check_and_decrement_quota(user_id)


async def refund_quota(user_id: str, reason: str = "search_failed") -> Dict[str, Any]:
    """Refund quota to user"""
    return await QuotaService.refund_quota(user_id, reason)


async def update_subscription(user_id: str, plan_type: str, searches_limit: int, subscription_status: str = "active") -> Dict[str, Any]:
    """Update user subscription"""
    return await QuotaService.update_subscription(user_id, plan_type, searches_limit, subscription_status)


# Create a singleton instance for easy import
quota_service = QuotaService()
