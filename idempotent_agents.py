"""
Idempotent Agents - Token limiting, execution caching, and retry-safe agent orchestration
"""

import os
import hashlib
import json
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Token limits per plan
PLAN_LIMITS = {
    "free": {
        "tokens_per_search": 10_000,   # ~7,500 words
        "estimated_cost": 0.02
    },
    "pro": {
        "tokens_per_search": 50_000,   # ~37,500 words
        "estimated_cost": 0.10
    },
    "enterprise": {
        "tokens_per_search": 200_000,  # ~150,000 words
        "estimated_cost": 0.40
    }
}


class AgentExecutionCache:
    """
    Cache agent execution results to prevent duplicate work on retries
    In production, use Redis for distributed caching
    """
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    def _get_cache_key(
        self,
        search_id: str,
        agent_name: str,
        step: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate cache key for agent execution"""
        key_parts = [search_id, agent_name, step]
        
        if inputs:
            # Hash inputs to create consistent key
            inputs_hash = hashlib.md5(
                json.dumps(inputs, sort_keys=True).encode()
            ).hexdigest()
            key_parts.append(inputs_hash)
        
        return ":".join(key_parts)
    
    def get(
        self,
        search_id: str,
        agent_name: str,
        step: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached result"""
        cache_key = self._get_cache_key(search_id, agent_name, step, inputs)
        result = self.cache.get(cache_key)
        
        if result:
            logger.info(f"Cache HIT for {agent_name}:{step}")
        
        return result
    
    def set(
        self,
        search_id: str,
        agent_name: str,
        step: str,
        result: Dict[str, Any],
        inputs: Optional[Dict[str, Any]] = None
    ) -> None:
        """Cache result"""
        cache_key = self._get_cache_key(search_id, agent_name, step, inputs)
        self.cache[cache_key] = result
        logger.info(f"Cached result for {agent_name}:{step}")
    
    def clear_search(self, search_id: str) -> None:
        """Clear all cached results for a search"""
        keys_to_delete = [
            key for key in self.cache.keys()
            if key.startswith(f"{search_id}:")
        ]
        
        for key in keys_to_delete:
            del self.cache[key]
        
        logger.info(f"Cleared cache for search {search_id}")


class TokenUsageLimiter:
    """Track and enforce token usage limits per search"""
    
    def __init__(self):
        self.usage: Dict[str, int] = {}
    
    def track_usage(
        self,
        search_id: str,
        tokens_used: int
    ) -> int:
        """
        Track token usage for a search
        
        Args:
            search_id: Search identifier
            tokens_used: Tokens consumed
            
        Returns:
            Total tokens used so far
        """
        if search_id not in self.usage:
            self.usage[search_id] = 0
        
        self.usage[search_id] += tokens_used
        
        logger.info(f"Search {search_id}: {tokens_used} tokens used (total: {self.usage[search_id]})")
        
        return self.usage[search_id]
    
    def get_usage(self, search_id: str) -> int:
        """Get current token usage"""
        return self.usage.get(search_id, 0)
    
    def check_limit(
        self,
        search_id: str,
        plan_type: str,
        estimated_tokens: int = 0
    ) -> bool:
        """
        Check if adding more tokens would exceed limit
        
        Args:
            search_id: Search identifier
            plan_type: User's plan type
            estimated_tokens: Estimated tokens for next operation
            
        Returns:
            True if within limit
        """
        current = self.get_usage(search_id)
        limit = PLAN_LIMITS.get(plan_type, PLAN_LIMITS["free"])["tokens_per_search"]
        
        would_exceed = (current + estimated_tokens) > limit
        
        if would_exceed:
            logger.warning(
                f"Token limit check failed for search {search_id}: "
                f"{current + estimated_tokens}/{limit} ({plan_type} plan)"
            )
        
        return not would_exceed
    
    def enforce_limit(
        self,
        search_id: str,
        plan_type: str,
        estimated_tokens: int = 0
    ) -> None:
        """
        Enforce token limit, raise exception if exceeded
        
        Raises:
            HTTPException: If limit would be exceeded
        """
        from fastapi import HTTPException
        
        if not self.check_limit(search_id, plan_type, estimated_tokens):
            current = self.get_usage(search_id)
            limit = PLAN_LIMITS[plan_type]["tokens_per_search"]
            
            raise HTTPException(
                status_code=429,
                detail=f"Token limit exceeded: {current + estimated_tokens}/{limit} tokens for {plan_type} plan"
            )
    
    def clear_search(self, search_id: str) -> None:
        """Clear usage tracking for a search"""
        if search_id in self.usage:
            del self.usage[search_id]


# Global instances
execution_cache = AgentExecutionCache()
token_limiter = TokenUsageLimiter()


def idempotent_agent(agent_name: str):
    """
    Decorator to make agent execution idempotent and token-limited
    
    Usage:
        @idempotent_agent("QueryAnalyzer")
        async def analyze_query(search_id: str, query: str, plan_type: str):
            # Agent logic here
            return {"queries": [...], "tokens_used": 500}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(
            search_id: str,
            *args,
            plan_type: str = "free",
            step: str = "default",
            **kwargs
        ):
            # Check cache first
            inputs = {"args": args, "kwargs": kwargs}
            cached_result = execution_cache.get(search_id, agent_name, step, inputs)
            
            if cached_result:
                logger.info(f"Returning cached result for {agent_name}:{step}")
                return cached_result
            
            # Check token limit before execution
            # Estimate tokens for this agent (customize per agent)
            estimated_tokens = kwargs.get("estimated_tokens", 1000)
            token_limiter.enforce_limit(search_id, plan_type, estimated_tokens)
            
            # Execute agent
            logger.info(f"Executing {agent_name}:{step}")
            result = await func(search_id, *args, plan_type=plan_type, step=step, **kwargs)
            
            # Track token usage
            tokens_used = result.get("tokens_used", 0)
            token_limiter.track_usage(search_id, tokens_used)
            
            # Cache result
            execution_cache.set(search_id, agent_name, step, result, inputs)
            
            return result
        
        return wrapper
    
    return decorator


class IdempotentOrchestrator:
    """
    Wrapper around base orchestrator to add idempotency and token tracking
    """
    
    def __init__(self, base_orchestrator):
        self.base_orchestrator = base_orchestrator
        self.cache = execution_cache
        self.token_limiter = token_limiter
    
    async def execute(
        self,
        search_id: str,
        query: str,
        plan_type: str = "free",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute search with idempotency and token limiting
        
        Args:
            search_id: Search identifier
            query: Search query
            plan_type: User's plan type
            metadata: Optional metadata
            
        Returns:
            Search results
        """
        try:
            # Check if search already completed
            cached_result = self.cache.get(search_id, "Orchestrator", "complete")
            if cached_result:
                logger.info(f"Returning cached orchestrator result for {search_id}")
                return cached_result
            
            # Execute base orchestrator
            result = await self.base_orchestrator.execute(
                search_id=search_id,
                query=query,
                plan_type=plan_type,
                metadata=metadata
            )
            
            # Cache complete result
            self.cache.set(search_id, "Orchestrator", "complete", result)
            
            # Log final token usage
            total_tokens = self.token_limiter.get_usage(search_id)
            limit = PLAN_LIMITS[plan_type]["tokens_per_search"]
            logger.info(
                f"Search {search_id} completed: {total_tokens}/{limit} tokens used ({plan_type} plan)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Orchestrator execution failed: {str(e)}")
            
            # Clear cache on failure to allow retry
            self.cache.clear_search(search_id)
            self.token_limiter.clear_search(search_id)
            
            raise
    
    async def save_progress(
        self,
        search_id: str,
        agent_name: str,
        status: str,
        data: Dict[str, Any],
        tokens_used: int = 0
    ) -> None:
        """
        Save agent progress to database
        
        Args:
            search_id: Search identifier
            agent_name: Agent name
            status: Status (pending, processing, completed, failed)
            data: Progress data
            tokens_used: Tokens consumed
        """
        try:
            from supabase import create_client
            
            supabase = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            )
            
            progress_data = {
                "search_id": search_id,
                "agent_name": agent_name,
                "status": status,
                "data": data,
                "tokens_used": tokens_used,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table("agent_progress").insert(progress_data).execute()
            
            # Also track tokens
            if tokens_used > 0:
                self.token_limiter.track_usage(search_id, tokens_used)
            
        except Exception as e:
            logger.error(f"Error saving progress: {str(e)}")


# Convenience functions
def track_tokens(search_id: str, tokens_used: int) -> int:
    """Track token usage"""
    return token_limiter.track_usage(search_id, tokens_used)


def check_token_limit(search_id: str, plan_type: str, estimated_tokens: int = 0) -> bool:
    """Check token limit"""
    return token_limiter.check_limit(search_id, plan_type, estimated_tokens)


def get_token_usage(search_id: str) -> int:
    """Get token usage"""
    return token_limiter.get_usage(search_id)


def clear_search_cache(search_id: str) -> None:
    """Clear cache for search"""
    execution_cache.clear_search(search_id)
    token_limiter.clear_search(search_id)
