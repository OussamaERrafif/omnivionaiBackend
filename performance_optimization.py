"""
Performance Optimization - Redis caching, connection pooling, and background queues
"""

import os
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Optional Redis support
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Using in-memory cache.")


class RedisCache:
    """Redis-based caching for performance optimization"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.client: Optional[redis.Redis] = None
        self.available = REDIS_AVAILABLE and self.redis_url is not None
        
        # In-memory fallback
        self.memory_cache: Dict[str, Any] = {}
    
    async def connect(self) -> None:
        """Connect to Redis"""
        if not self.available:
            logger.info("Using in-memory cache (Redis not configured)")
            return
        
        try:
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.available = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.available and self.client:
                value = await self.client.get(key)
                return json.loads(value) if value else None
            else:
                return self.memory_cache.get(key)
        except Exception as e:
            logger.error(f"Cache GET error: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> bool:
        """Set value in cache with TTL"""
        try:
            json_value = json.dumps(value)
            
            if self.available and self.client:
                await self.client.set(key, json_value, ex=ttl)
            else:
                self.memory_cache[key] = value
                # Schedule cleanup for in-memory cache
                asyncio.create_task(self._cleanup_memory_cache(key, ttl))
            
            return True
        except Exception as e:
            logger.error(f"Cache SET error: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.available and self.client:
                await self.client.delete(key)
            else:
                self.memory_cache.pop(key, None)
            
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            if self.available and self.client:
                return await self.client.exists(key) > 0
            else:
                return key in self.memory_cache
        except Exception as e:
            logger.error(f"Cache EXISTS error: {str(e)}")
            return False
    
    async def _cleanup_memory_cache(self, key: str, delay: int) -> None:
        """Cleanup in-memory cache after TTL"""
        await asyncio.sleep(delay)
        self.memory_cache.pop(key, None)
    
    async def set_progress(
        self,
        search_id: str,
        progress_data: Dict[str, Any]
    ) -> None:
        """Store search progress for SSE streaming"""
        key = f"progress:{search_id}"
        await self.set(key, progress_data, ttl=1800)  # 30 minutes
    
    async def get_progress(self, search_id: str) -> Optional[Dict[str, Any]]:
        """Get search progress"""
        key = f"progress:{search_id}"
        return await self.get(key)
    
    async def append_progress_event(
        self,
        search_id: str,
        event: Dict[str, Any]
    ) -> None:
        """Append progress event for streaming"""
        key = f"progress_stream:{search_id}"
        
        if self.available and self.client:
            # Use Redis list for streaming
            await self.client.rpush(key, json.dumps(event))
            await self.client.expire(key, 1800)  # 30 minutes
        else:
            # Fallback: store in memory
            if key not in self.memory_cache:
                self.memory_cache[key] = []
            self.memory_cache[key].append(event)
    
    async def get_progress_stream(self, search_id: str) -> List[Dict[str, Any]]:
        """Get all progress events"""
        key = f"progress_stream:{search_id}"
        
        if self.available and self.client:
            events = await self.client.lrange(key, 0, -1)
            return [json.loads(e) for e in events]
        else:
            return self.memory_cache.get(key, [])
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.client:
            await self.client.close()


class SearchQueue:
    """
    Background queue for long-running searches
    Uses Redis for distributed queue management
    """
    
    def __init__(self, cache: RedisCache):
        self.cache = cache
    
    async def enqueue_search(
        self,
        search_id: str,
        user_id: str,
        query: str,
        plan_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Enqueue search for background processing
        
        Returns:
            Job ID
        """
        job_id = f"job:{search_id}"
        
        job_data = {
            "search_id": search_id,
            "user_id": user_id,
            "query": query,
            "plan_type": plan_type,
            "metadata": metadata or {},
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.cache.set(job_id, job_data, ttl=7200)  # 2 hours
        
        logger.info(f"Search {search_id} enqueued")
        
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        return await self.cache.get(job_id)
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update job status"""
        job_data = await self.cache.get(job_id)
        
        if job_data:
            job_data["status"] = status
            job_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            if result:
                job_data["result"] = result
            
            await self.cache.set(job_id, job_data, ttl=7200)


class ConnectionPool:
    """
    Connection pool for database connections
    Improves performance by reusing connections
    """
    
    def __init__(self, pool_size: int = 10):
        self.pool_size = pool_size
        self.connections: List[Any] = []
        self.available: List[Any] = []
        self.in_use: set = set()
    
    async def get_connection(self):
        """Get connection from pool"""
        if self.available:
            conn = self.available.pop()
            self.in_use.add(id(conn))
            return conn
        
        if len(self.connections) < self.pool_size:
            # Create new connection
            from supabase import create_client
            
            conn = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            )
            self.connections.append(conn)
            self.in_use.add(id(conn))
            return conn
        
        # Wait for available connection
        while not self.available:
            await asyncio.sleep(0.1)
        
        return await self.get_connection()
    
    async def release_connection(self, conn):
        """Release connection back to pool"""
        conn_id = id(conn)
        if conn_id in self.in_use:
            self.in_use.remove(conn_id)
            self.available.append(conn)


class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
    
    def record_metric(self, name: str, value: float) -> None:
        """Record a performance metric"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append(value)
        
        # Keep only last 1000 values
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
    
    def get_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        values = self.metrics[name]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p95": sorted(values)[int(len(values) * 0.95)] if len(values) > 20 else max(values)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get all metrics statistics"""
        return {
            name: self.get_stats(name)
            for name in self.metrics.keys()
        }


# Global instances
redis_cache = RedisCache()
performance_monitor = PerformanceMonitor()
connection_pool = ConnectionPool()


async def initialize_performance_layer():
    """Initialize performance optimization layer"""
    await redis_cache.connect()
    logger.info("Performance layer initialized")


async def cleanup_performance_layer():
    """Cleanup performance layer"""
    await redis_cache.close()
    logger.info("Performance layer cleaned up")


# Convenience functions for easy import
async def init_redis_cache():
    """Initialize Redis cache"""
    await redis_cache.connect()


async def cleanup_redis_cache():
    """Cleanup Redis cache"""
    await redis_cache.close()


def get_redis_cache() -> RedisCache:
    """Get Redis cache instance"""
    return redis_cache


# Performance monitor instance
perf_monitor = performance_monitor


# Query utility functions
def hash_query(query: str) -> str:
    """Hash a query for caching"""
    import hashlib
    return hashlib.sha256(query.encode()).hexdigest()


def normalize_query(query: str) -> str:
    """Normalize query for consistent caching"""
    return query.strip().lower()
