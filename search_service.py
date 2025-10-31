"""
Search Service - Complete search lifecycle management
Handles search creation, execution, updates, and error handling
"""

import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from supabase import create_client, Client
import logging
from quota_service import check_and_decrement_quota, refund_quota, QuotaExceededError

logger = logging.getLogger(__name__)

# Initialize Supabase client with service role
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


class SearchService:
    """Service for managing search operations"""
    
    @staticmethod
    async def create_search(
        user_id: str,
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new search record in pending state
        
        Args:
            user_id: User UUID
            query: Search query
            metadata: Optional metadata
            
        Returns:
            Dict with search_id and initial status
        """
        search_id = str(uuid.uuid4())
        
        try:
            search_data = {
                "id": search_id,
                "user_id": user_id,
                "query": query,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {}
            }
            
            result = supabase.table("encrypted_search_history").insert(
                search_data
            ).execute()
            
            logger.info(f"Created search {search_id} for user {user_id}")
            
            return {
                "search_id": search_id,
                "status": "pending",
                "created_at": search_data["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Error creating search: {str(e)}")
            raise
    
    @staticmethod
    async def execute_search(
        user_id: str,
        query: str,
        plan_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete search lifecycle:
        1. Check and decrement quota
        2. Create search record (pending)
        3. Execute search
        4. Update with results or handle error
        5. Refund quota on failure
        
        Args:
            user_id: User UUID
            query: Search query
            plan_type: User's plan type
            metadata: Optional metadata
            
        Returns:
            Dict with search results
            
        Raises:
            QuotaExceededError: If user has no quota
        """
        search_id = None
        quota_decremented = False
        
        try:
            # Step 1: Check and decrement quota (atomic)
            quota_result = await check_and_decrement_quota(user_id)
            quota_decremented = True
            logger.info(f"Quota decremented. Remaining: {quota_result['searches_remaining']}")
            
            # Step 2: Create search record
            search_result = await SearchService.create_search(user_id, query, metadata)
            search_id = search_result["search_id"]
            
            # Step 3: Execute search (placeholder - integrate with your agent orchestrator)
            # This would call your multi-agent pipeline
            from agents.orchestrator import AgentOrchestrator
            
            orchestrator = AgentOrchestrator()
            search_results = await orchestrator.execute(
                search_id=search_id,
                query=query,
                plan_type=plan_type
            )
            
            # Step 4: Update with success
            await SearchService._update_search_success(
                search_id=search_id,
                results=search_results
            )
            
            return {
                "search_id": search_id,
                "status": "success",
                "results": search_results,
                "quota_remaining": quota_result["searches_remaining"]
            }
            
        except QuotaExceededError:
            # Don't refund if quota was already exceeded
            raise
            
        except Exception as e:
            logger.error(f"Search execution failed: {str(e)}")
            
            # Step 5: Handle failure
            if search_id:
                await SearchService._update_search_failure(
                    search_id=search_id,
                    error=str(e)
                )
            
            # Refund quota if it was decremented
            if quota_decremented:
                await refund_quota(user_id, reason=f"search_failed: {str(e)}")
                logger.info(f"Quota refunded for failed search")
            
            raise
    
    @staticmethod
    async def _update_search_success(
        search_id: str,
        results: Dict[str, Any]
    ) -> None:
        """Update search record with successful results"""
        try:
            update_data = {
                "status": "success",
                "results": results,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table("encrypted_search_history").update(
                update_data
            ).eq("id", search_id).execute()
            
            logger.info(f"Search {search_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error updating search success: {str(e)}")
            raise
    
    @staticmethod
    async def _update_search_failure(
        search_id: str,
        error: str
    ) -> None:
        """Update search record with failure information"""
        try:
            update_data = {
                "status": "failed",
                "error": error,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table("encrypted_search_history").update(
                update_data
            ).eq("id", search_id).execute()
            
            logger.info(f"Search {search_id} marked as failed")
            
        except Exception as e:
            logger.error(f"Error updating search failure: {str(e)}")
            raise
    
    @staticmethod
    async def get_search_by_id(search_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a search by ID (with user verification)"""
        try:
            result = supabase.table("encrypted_search_history").select(
                "*"
            ).eq("id", search_id).eq("user_id", user_id).single().execute()
            
            return result.data if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting search {search_id}: {str(e)}")
            return None
    
    @staticmethod
    async def update_search_progress(
        search_id: str,
        progress: int,
        current_agent: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update search progress (for SSE streaming)"""
        try:
            update_data = {
                "progress": progress,
                "current_agent": current_agent,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if metadata:
                update_data["metadata"] = metadata
            
            supabase.table("encrypted_search_history").update(
                update_data
            ).eq("id", search_id).execute()
            
        except Exception as e:
            logger.error(f"Error updating search progress: {str(e)}")


# Convenience functions
async def execute_search(user_id: str, query: str, plan_type: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a complete search"""
    return await SearchService.execute_search(user_id, query, plan_type, metadata)


async def get_search_by_id(search_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get search by ID"""
    return await SearchService.get_search_by_id(search_id, user_id)


async def update_search_progress(search_id: str, progress: int, current_agent: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Update search progress"""
    return await SearchService.update_search_progress(search_id, progress, current_agent, metadata)


# Create a singleton instance for easy import
search_service = SearchService()
