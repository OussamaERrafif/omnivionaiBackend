"""
History Service - Backend-authoritative search history management
All history operations go through backend only
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client with service role
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


class HistoryService:
    """Service for managing search history"""
    
    @staticmethod
    async def save_search_history(
        user_id: str,
        query: str,
        results: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save search to history (backend-authoritative)
        
        Args:
            user_id: User UUID
            query: Search query
            results: Search results
            metadata: Optional metadata
            
        Returns:
            Dict with saved history information
        """
        try:
            history_data = {
                "user_id": user_id,
                "query": query,
                "results": results,
                "metadata": metadata or {},
                "status": "success",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = supabase.table("encrypted_search_history").insert(
                history_data
            ).execute()
            
            logger.info(f"Search history saved for user {user_id}")
            
            return {
                "id": result.data[0]["id"] if result.data else None,
                "saved": True,
                "created_at": history_data["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Error saving search history: {str(e)}")
            raise
    
    @staticmethod
    async def get_search_history(
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get search history for a user
        
        Args:
            user_id: User UUID
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of search history records
        """
        try:
            result = supabase.table("encrypted_search_history").select(
                "*"
            ).eq("user_id", user_id).order(
                "created_at", desc=True
            ).range(offset, offset + limit - 1).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting search history: {str(e)}")
            raise
    
    @staticmethod
    async def delete_search_history_item(
        user_id: str,
        history_id: str
    ) -> Dict[str, Any]:
        """
        Delete a specific search history item
        
        Args:
            user_id: User UUID
            history_id: History item ID
            
        Returns:
            Dict with deletion status
        """
        try:
            # Verify ownership before deletion
            result = supabase.table("encrypted_search_history").delete().eq(
                "id", history_id
            ).eq("user_id", user_id).execute()
            
            deleted = len(result.data) > 0 if result.data else False
            
            if deleted:
                logger.info(f"Search history item {history_id} deleted for user {user_id}")
            else:
                logger.warning(f"Search history item {history_id} not found or unauthorized")
            
            return {
                "deleted": deleted,
                "history_id": history_id
            }
            
        except Exception as e:
            logger.error(f"Error deleting search history: {str(e)}")
            raise
    
    @staticmethod
    async def delete_all_search_history(user_id: str) -> Dict[str, Any]:
        """
        Delete all search history for a user
        
        Args:
            user_id: User UUID
            
        Returns:
            Dict with deletion status
        """
        try:
            result = supabase.table("encrypted_search_history").delete().eq(
                "user_id", user_id
            ).execute()
            
            count = len(result.data) if result.data else 0
            
            logger.info(f"Deleted {count} search history items for user {user_id}")
            
            return {
                "deleted": True,
                "count": count
            }
            
        except Exception as e:
            logger.error(f"Error deleting all search history: {str(e)}")
            raise
    
    @staticmethod
    async def get_search_count(user_id: str) -> int:
        """
        Get total search count for a user
        
        Args:
            user_id: User UUID
            
        Returns:
            Total number of searches
        """
        try:
            result = supabase.table("encrypted_search_history").select(
                "id", count="exact"
            ).eq("user_id", user_id).execute()
            
            return result.count if result.count else 0
            
        except Exception as e:
            logger.error(f"Error getting search count: {str(e)}")
            return 0


# Convenience functions
async def save_search_history(user_id: str, query: str, results: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Save search to history"""
    return await HistoryService.save_search_history(user_id, query, results, metadata)


async def get_search_history(user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get search history"""
    return await HistoryService.get_search_history(user_id, limit, offset)


async def delete_search_history_item(user_id: str, history_id: str) -> Dict[str, Any]:
    """Delete search history item"""
    return await HistoryService.delete_search_history_item(user_id, history_id)


async def delete_all_search_history(user_id: str) -> Dict[str, Any]:
    """Delete all search history"""
    return await HistoryService.delete_all_search_history(user_id)


async def clear_all_history(user_id: str) -> Dict[str, Any]:
    """Alias for delete_all_search_history (for compatibility)"""
    return await HistoryService.delete_all_search_history(user_id)
