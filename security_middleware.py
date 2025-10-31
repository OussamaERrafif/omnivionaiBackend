"""
Security Middleware - Rate limiting, input sanitization, and security headers
"""

import time
import re
from typing import Dict, Any, Optional
from collections import defaultdict
from fastapi import Request, HTTPException
from fastapi.responses import Response
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter using in-memory storage
    For production, use Redis for distributed rate limiting
    """
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.limits = {
            "free": {"requests": 10, "window": 60},      # 10 requests per minute
            "pro": {"requests": 50, "window": 60},       # 50 requests per minute
            "enterprise": {"requests": 200, "window": 60} # 200 requests per minute
        }
    
    def check_rate_limit(
        self,
        user_id: str,
        plan_type: str = "free"
    ) -> bool:
        """
        Check if user has exceeded rate limit
        
        Args:
            user_id: User ID
            plan_type: User's plan type
            
        Returns:
            True if within limit, False if exceeded
        """
        now = time.time()
        window = self.limits.get(plan_type, self.limits["free"])["window"]
        max_requests = self.limits.get(plan_type, self.limits["free"])["requests"]
        
        # Clean old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < window
        ]
        
        # Check limit
        if len(self.requests[user_id]) >= max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id} (plan: {plan_type})")
            return False
        
        # Add current request
        self.requests[user_id].append(now)
        return True
    
    def get_remaining_requests(
        self,
        user_id: str,
        plan_type: str = "free"
    ) -> int:
        """Get number of remaining requests in current window"""
        now = time.time()
        window = self.limits.get(plan_type, self.limits["free"])["window"]
        max_requests = self.limits.get(plan_type, self.limits["free"])["requests"]
        
        # Clean old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < window
        ]
        
        return max(0, max_requests - len(self.requests[user_id]))


class InputSanitizer:
    """Input sanitization to prevent injection attacks"""
    
    @staticmethod
    def sanitize_query(query: str, max_length: int = 1000) -> str:
        """
        Sanitize search query
        
        Args:
            query: User input query
            max_length: Maximum allowed length
            
        Returns:
            Sanitized query
            
        Raises:
            HTTPException: If input is invalid
        """
        if not query or not isinstance(query, str):
            raise HTTPException(
                status_code=400,
                detail="Query must be a non-empty string"
            )
        
        # Trim whitespace
        query = query.strip()
        
        # Check length
        if len(query) > max_length:
            raise HTTPException(
                status_code=400,
                detail=f"Query too long (max {max_length} characters)"
            )
        
        if len(query) < 3:
            raise HTTPException(
                status_code=400,
                detail="Query too short (min 3 characters)"
            )
        
        # ✅ SECURITY FIX: Enhanced dangerous pattern detection
        dangerous_patterns = [
            # SQL Injection
            r";\s*DROP", r";\s*DELETE", r";\s*UPDATE", r";\s*INSERT",
            r"UNION\s+SELECT", r"--", r"/\*", r"\*/", r"xp_", r"sp_",
            r";\s*EXEC", r";\s*EXECUTE", r"INFORMATION_SCHEMA",
            r";\s*ALTER", r";\s*CREATE", r";\s*TRUNCATE",
            
            # NoSQL Injection
            r"\$where", r"\$ne", r"\$gt", r"\$lt", r"\$regex", r"\$nin",
            
            # Command Injection
            r"`.*`", r"\$\(.*\)", r"&&", r"\|\|", r";\s*\w+",
            
            # Path Traversal
            r"\.\./", r"\.\.\\", r"%2e%2e", r"%252e",
            
            # LDAP Injection
            r"\(\|", r"\(&", r"\(!", r"\*\)",
            
            # XSS Prevention (belt and suspenders)
            r"<script", r"javascript:", r"onerror\s*=", r"onload\s*=",
            r"<iframe", r"<object", r"<embed",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Suspicious query detected: {query[:100]}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid query format detected"
                )
        
        return query
    
    @staticmethod
    def sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sanitize metadata dictionary
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Sanitized metadata
        """
        if not metadata:
            return {}
        
        # ✅ SECURITY FIX: Enhanced metadata validation
        MAX_KEY_LENGTH = 100
        MAX_VALUE_LENGTH = 1000
        MAX_METADATA_FIELDS = 50
        MAX_TOTAL_SIZE = 10000
        
        # Check number of fields
        if len(metadata) > MAX_METADATA_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=f"Too many metadata fields (max {MAX_METADATA_FIELDS})"
            )
        
        # Check total size
        if len(str(metadata)) > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Metadata too large (max {MAX_TOTAL_SIZE} bytes)"
            )
        
        sanitized = {}
        for key, value in metadata.items():
            # Validate key
            if not isinstance(key, str):
                continue
            
            if len(key) > MAX_KEY_LENGTH:
                logger.warning(f"Metadata key too long: {key[:50]}...")
                continue
            
            # Validate and sanitize value
            if isinstance(value, str):
                if len(value) > MAX_VALUE_LENGTH:
                    value = value[:MAX_VALUE_LENGTH]
                # Remove potentially dangerous characters
                value = re.sub(r'[<>\"\'`]', '', value)
            elif isinstance(value, (int, float, bool)):
                # Safe types - allow as is
                pass
            elif isinstance(value, (list, dict)):
                # Convert complex types to safe string representation
                value = str(value)[:MAX_VALUE_LENGTH]
            else:
                # Unknown type - skip
                continue
            
            sanitized[key] = value
        
        return sanitized


class SecurityHeaders:
    """Add security headers to responses"""
    
    @staticmethod
    def add_security_headers(response: Response) -> Response:
        """
        Add security headers to response
        
        Args:
            response: FastAPI response
            
        Returns:
            Response with security headers
        """
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


# Global instances
rate_limiter = RateLimiter()
input_sanitizer = InputSanitizer()
security_headers = SecurityHeaders()


def check_rate_limit(user_id: str, plan_type: str = "free") -> bool:
    """Check rate limit for user"""
    return rate_limiter.check_rate_limit(user_id, plan_type)


def sanitize_query(query: str, max_length: int = 1000) -> str:
    """Sanitize search query"""
    return input_sanitizer.sanitize_query(query, max_length)


def sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Sanitize metadata"""
    return input_sanitizer.sanitize_metadata(metadata)


def add_security_headers(response: Response) -> Response:
    """Add security headers to response"""
    return security_headers.add_security_headers(response)


# Create middleware class for FastAPI
class SecurityMiddleware:
    """FastAPI middleware for security features"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add security processing here if needed
            pass
        await self.app(scope, receive, send)


# Webhook idempotency tracker
class WebhookIdempotency:
    """Track processed webhooks"""
    
    def __init__(self):
        self.processed_events: set = set()
    
    def is_processed(self, event_id: str) -> bool:
        """Check if event was processed"""
        return event_id in self.processed_events
    
    def mark_processed(self, event_id: str) -> None:
        """Mark event as processed"""
        self.processed_events.add(event_id)


# Security logger
class SecurityLogger:
    """Log security events"""
    
    def __init__(self):
        self.logger = logging.getLogger("security")
    
    def log_event(self, event_type: str, user_id: str = None, details: str = None):
        """Log a security event"""
        self.logger.info(f"Security Event: {event_type} | User: {user_id} | Details: {details}")


class SecurityHeadersMiddleware:
    """
    Add security headers to all HTTP responses
    Protects against clickjacking, XSS, MIME sniffing, etc.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                
                # Prevent clickjacking attacks
                headers[b"x-frame-options"] = b"DENY"
                
                # Prevent MIME type sniffing
                headers[b"x-content-type-options"] = b"nosniff"
                
                # XSS Protection (legacy but still useful)
                headers[b"x-xss-protection"] = b"1; mode=block"
                
                # Referrer Policy
                headers[b"referrer-policy"] = b"strict-origin-when-cross-origin"
                
                # Permissions Policy (restrict browser features)
                headers[b"permissions-policy"] = b"geolocation=(), microphone=(), camera=()"
                
                # Content Security Policy
                import os
                if os.getenv("ENV") == "production":
                    csp = (
                        "default-src 'self'; "
                        "script-src 'self'; "
                        "style-src 'self' 'unsafe-inline'; "
                        "img-src 'self' data: https:; "
                        "font-src 'self' data:; "
                        "connect-src 'self' https://api.openai.com; "
                        "frame-ancestors 'none'"
                    )
                else:
                    # More permissive for development
                    csp = (
                        "default-src 'self'; "
                        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                        "style-src 'self' 'unsafe-inline'; "
                        "img-src 'self' data: https:; "
                        "font-src 'self' data:; "
                        "connect-src 'self' https://api.openai.com"
                    )
                headers[b"content-security-policy"] = csp.encode()
                
                message["headers"] = list(headers.items())
            
            await send(message)
        
        await self.app(scope, receive, send_with_headers)


# Import auth decorators from auth_utils for convenience
from auth_utils import require_auth, optional_auth

# Global instances
webhook_idempotency = WebhookIdempotency()
security_logger = SecurityLogger()
