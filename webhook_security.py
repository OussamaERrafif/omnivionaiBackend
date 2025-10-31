"""
Webhook Security - Signature verification, idempotency, and replay protection
"""

import os
import hmac
import hashlib
import time
import json
from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone
from fastapi import Request, HTTPException
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
LEMON_SQUEEZY_WEBHOOK_SECRET = os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET")

if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, LEMON_SQUEEZY_WEBHOOK_SECRET]):
    raise ValueError("Required environment variables not set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


class WebhookVerifier:
    """Verify webhook signatures"""
    
    def __init__(self, secret: str):
        self.secret = secret.encode('utf-8')
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify HMAC-SHA256 signature
        
        Args:
            payload: Raw request body
            signature: Signature from header
            
        Returns:
            True if signature is valid
        """
        try:
            # Compute HMAC-SHA256
            expected_signature = hmac.new(
                self.secret,
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Constant-time comparison to prevent timing attacks
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Error verifying signature: {str(e)}")
            return False


class ReplayProtection:
    """Protect against replay attacks"""
    
    @staticmethod
    def validate_timestamp(timestamp: int, max_age: int = 300) -> bool:
        """
        Validate webhook timestamp (prevent replay attacks)
        
        Args:
            timestamp: Webhook timestamp
            max_age: Maximum age in seconds (default 5 minutes)
            
        Returns:
            True if timestamp is valid
        """
        now = int(time.time())
        age = now - timestamp
        
        if age > max_age:
            logger.warning(f"Webhook too old: {age} seconds")
            return False
        
        if age < -60:  # Allow 1 minute clock skew
            logger.warning(f"Webhook timestamp in future: {age} seconds")
            return False
        
        return True


class WebhookIdempotency:
    """Track processed webhooks to prevent duplicate processing"""
    
    def __init__(self):
        # In production, use Redis or database
        self.processed_events: Set[str] = set()
    
    async def is_processed(self, event_id: str) -> bool:
        """
        Check if event has already been processed
        
        Args:
            event_id: Unique event identifier
            
        Returns:
            True if already processed
        """
        # Check in-memory cache
        if event_id in self.processed_events:
            return True
        
        # Check database
        try:
            result = supabase.table("lemon_squeezy_webhooks").select(
                "event_id"
            ).eq("event_id", event_id).execute()
            
            return len(result.data) > 0 if result.data else False
            
        except Exception as e:
            logger.error(f"Error checking webhook idempotency: {str(e)}")
            return False
    
    async def mark_processed(
        self,
        event_id: str,
        event_name: str,
        payload: Dict[str, Any]
    ) -> None:
        """
        Mark event as processed
        
        Args:
            event_id: Event identifier
            event_name: Event name
            payload: Event payload
        """
        # Add to in-memory cache
        self.processed_events.add(event_id)
        
        # Store in database
        try:
            supabase.table("lemon_squeezy_webhooks").insert({
                "event_id": event_id,
                "event_name": event_name,
                "payload": payload,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            
            logger.info(f"Webhook {event_id} marked as processed")
            
        except Exception as e:
            logger.error(f"Error marking webhook as processed: {str(e)}")


class WebhookHandler:
    """Complete webhook processing"""
    
    def __init__(self):
        self.verifier = WebhookVerifier(LEMON_SQUEEZY_WEBHOOK_SECRET)
        self.replay_protection = ReplayProtection()
        self.idempotency = WebhookIdempotency()
        
        # Supported events
        self.supported_events = {
            "subscription_created",
            "subscription_updated",
            "subscription_cancelled",
            "subscription_resumed",
            "subscription_expired",
            "subscription_paused",
            "subscription_unpaused",
            "order_created",
            "order_refunded"
        }
    
    async def process_webhook(self, request: Request) -> Dict[str, Any]:
        """
        Process incoming webhook with full security validation
        
        Args:
            request: FastAPI request
            
        Returns:
            Processing result
            
        Raises:
            HTTPException: If validation fails
        """
        # Step 1: Get raw body and signature
        body = await request.body()
        signature = request.headers.get("X-Signature")
        
        if not signature:
            raise HTTPException(
                status_code=401,
                detail="Missing X-Signature header"
            )
        
        # Step 2: Verify signature
        if not self.verifier.verify_signature(body, signature):
            logger.error("Invalid webhook signature")
            raise HTTPException(
                status_code=401,
                detail="Invalid signature"
            )
        
        # Step 3: Parse payload
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON payload"
            )
        
        # Step 4: Extract event metadata
        meta = payload.get("meta", {})
        event_id = meta.get("event_id")
        event_name = meta.get("event_name")
        timestamp = meta.get("timestamp")
        
        if not all([event_id, event_name]):
            raise HTTPException(
                status_code=400,
                detail="Missing event metadata"
            )
        
        # Step 5: Validate timestamp (replay protection)
        if timestamp and not self.replay_protection.validate_timestamp(timestamp):
            raise HTTPException(
                status_code=400,
                detail="Webhook expired or invalid timestamp"
            )
        
        # Step 6: Check idempotency
        if await self.idempotency.is_processed(event_id):
            logger.info(f"Webhook {event_id} already processed")
            return {
                "status": "already_processed",
                "event_id": event_id
            }
        
        # Step 7: Process event
        result = await self._process_event(event_name, payload)
        
        # Step 8: Mark as processed
        await self.idempotency.mark_processed(event_id, event_name, payload)
        
        return {
            "status": "processed",
            "event_id": event_id,
            "event_name": event_name,
            "result": result
        }
    
    async def _process_event(
        self,
        event_name: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process specific event type
        
        Args:
            event_name: Event name
            payload: Event payload
            
        Returns:
            Processing result
        """
        if event_name not in self.supported_events:
            logger.warning(f"Unsupported event: {event_name}")
            return {"status": "skipped", "reason": "unsupported_event"}
        
        try:
            # Extract subscription/order data
            data = payload.get("data", {})
            attributes = data.get("attributes", {})
            
            # Extract user information
            user_id = attributes.get("user_id")
            customer_id = attributes.get("customer_id")
            
            if not user_id:
                logger.warning(f"No user_id in webhook payload")
                return {"status": "skipped", "reason": "no_user_id"}
            
            # Handle different event types
            if event_name in ["subscription_created", "subscription_updated", "subscription_resumed", "subscription_unpaused"]:
                return await self._handle_subscription_active(user_id, attributes)
            
            elif event_name in ["subscription_cancelled", "subscription_expired", "subscription_paused"]:
                return await self._handle_subscription_inactive(user_id, attributes)
            
            elif event_name == "order_created":
                return await self._handle_order_created(user_id, attributes)
            
            elif event_name == "order_refunded":
                return await self._handle_order_refunded(user_id, attributes)
            
            return {"status": "processed"}
            
        except Exception as e:
            logger.error(f"Error processing event {event_name}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing webhook: {str(e)}"
            )
    
    async def _handle_subscription_active(
        self,
        user_id: str,
        attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle active subscription events"""
        from quota_service import update_subscription
        
        # Extract plan information
        variant_name = attributes.get("variant_name", "").lower()
        
        # Map variant to plan type and limits
        if "pro" in variant_name:
            plan_type = "pro"
            searches_limit = 100
        elif "enterprise" in variant_name:
            plan_type = "enterprise"
            searches_limit = 500
        else:
            plan_type = "free"
            searches_limit = 10
        
        # Update subscription
        result = await update_subscription(
            user_id=user_id,
            plan_type=plan_type,
            searches_limit=searches_limit,
            subscription_status="active"
        )
        
        logger.info(f"Subscription activated for user {user_id}: {plan_type}")
        
        return result
    
    async def _handle_subscription_inactive(
        self,
        user_id: str,
        attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle inactive subscription events"""
        from quota_service import update_subscription
        
        # Downgrade to free plan
        result = await update_subscription(
            user_id=user_id,
            plan_type="free",
            searches_limit=10,
            subscription_status="cancelled"
        )
        
        logger.info(f"Subscription cancelled for user {user_id}")
        
        return result
    
    async def _handle_order_created(
        self,
        user_id: str,
        attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle order creation"""
        # Store order in database
        try:
            order_data = {
                "user_id": user_id,
                "order_id": attributes.get("order_id"),
                "amount": attributes.get("total"),
                "currency": attributes.get("currency"),
                "status": "completed",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table("user_payments").insert(order_data).execute()
            
            logger.info(f"Order created for user {user_id}")
            
            return {"status": "order_recorded"}
            
        except Exception as e:
            logger.error(f"Error recording order: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_order_refunded(
        self,
        user_id: str,
        attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle order refund"""
        from quota_service import update_subscription
        
        # Downgrade to free plan
        result = await update_subscription(
            user_id=user_id,
            plan_type="free",
            searches_limit=10,
            subscription_status="refunded"
        )
        
        logger.info(f"Order refunded for user {user_id}")
        
        return result


# Global webhook handler instance
webhook_handler = WebhookHandler()


async def process_webhook(request: Request) -> Dict[str, Any]:
    """Process webhook"""
    return await webhook_handler.process_webhook(request)
