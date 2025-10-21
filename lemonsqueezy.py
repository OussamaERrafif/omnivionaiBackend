"""
Helpers for LemonSqueezy integration.

This module provides two main helpers:
- create_checkout: create a hosted checkout session (or proxy to configured helper)
- verify_webhook_signature: validate incoming webhook signature if secret configured

The implementation is defensive: if the LemonSqueezy API key or explicit proxy
URL are not configured it will return helpful errors so deployments remain secure.
"""
import os
import json
import hmac
import hashlib
from typing import Optional, Dict, Any
import requests

LEMONSQUEEZY_API_KEY = os.getenv("LEMONSQUEEZY_API_KEY", "")
LEMONSQUEEZY_WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET", "")
# Optional helper/proxy on your production backend that already knows how to
# create LemonSqueezy checkouts. If set, we forward creation requests to it.
LEMONSQUEEZY_HELPER_URL = os.getenv("LEMONSQUEEZY_HELPER_URL", "")

# Optional mapping if you prefer environment-driven plan -> product ids
# Example: LEMONSQUEEZY_PLAN_MAP='{"pro":"prod_abc","enterprise":"prod_xyz"}'
_plan_map_raw = os.getenv("LEMONSQUEEZY_PLAN_MAP", "")
try:
    LEMONSQUEEZY_PLAN_MAP = json.loads(_plan_map_raw) if _plan_map_raw else {}
except Exception:
    LEMONSQUEEZY_PLAN_MAP = {}


def create_checkout_payload(plan_type: str, user_id: Optional[str], return_url: Optional[str]) -> Dict[str, Any]:
    """Create provider-agnostic payload used for checkout creation.

    We include metadata.user_id (if available) so webhook events can be
    correlated back to the authenticated user.
    """
    payload = {
        "plan_type": plan_type,
        "metadata": {},
    }
    if user_id:
        payload["metadata"]["user_id"] = user_id
    if return_url:
        payload["return_url"] = return_url
    # If we have a product id mapping, include it for the helper to use
    if plan_type in LEMONSQUEEZY_PLAN_MAP:
        payload["product_id"] = LEMONSQUEEZY_PLAN_MAP[plan_type]
    return payload


def create_checkout(plan_type: str, user_id: Optional[str] = None, return_url: Optional[str] = None, forward_auth: Optional[str] = None) -> Dict[str, Any]:
    """Create a LemonSqueezy checkout session.

    Behavior:
    - If LEMONSQUEEZY_HELPER_URL is set, forward the request to {HELPER_URL}/lemonsqueezy/checkout
      (preserves Authorization header if provided).
    - Else, if LEMONSQUEEZY_API_KEY is set, attempt to call the LemonSqueezy REST API.
      We try a conservative POST to `/v1/checkouts` and include metadata. If the
      API responds with non-2xx, return the error.
    - If neither is configured, raise RuntimeError with instructions.
    """
    payload = create_checkout_payload(plan_type, user_id, return_url)

    # If a dedicated helper is configured, forward to it
    if LEMONSQUEEZY_HELPER_URL:
        url = LEMONSQUEEZY_HELPER_URL.rstrip("/") + "/lemonsqueezy/checkout"
        headers = {"content-type": "application/json"}
        if forward_auth:
            headers["authorization"] = forward_auth
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        try:
            resp.raise_for_status()
        except Exception:
            return {"error": True, "status_code": resp.status_code, "body": resp.text}
        return resp.json()

    # No helper; try calling LemonSqueezy REST API directly if API key exists
    if not LEMONSQUEEZY_API_KEY:
        raise RuntimeError("LEMONSQUEEZY_API_KEY or LEMONSQUEEZY_HELPER_URL must be configured on the backend to create checkouts.")

    # Best-effort attempt to create a hosted checkout using the REST API.
    # LemonSqueezy API uses /v1 namespace. We'll attempt /v1/checkouts which is
    # the documented resource for 'checkouts' in many integrations.
    api_url = "https://api.lemonsqueezy.com/v1/checkouts"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {LEMONSQUEEZY_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        # Keep the body simple and include metadata for later reconciliation
        "plan_type": plan_type,
        "metadata": payload.get("metadata", {}),
    }
    # If mapping provided, attach the product id
    if "product_id" in payload:
        body["product_id"] = payload["product_id"]
    if return_url:
        body["return_url"] = return_url

    resp = requests.post(api_url, headers=headers, json=body, timeout=15)
    # Return parsed JSON on success, otherwise error details
    try:
        resp.raise_for_status()
    except Exception:
        # Return response body for debugging
        return {"error": True, "status_code": resp.status_code, "body": resp.text}

    return resp.json()


def verify_webhook_signature(raw_body: bytes, header_signature: Optional[str]) -> bool:
    """Verify webhook signature using HMAC-SHA256 if secret configured.

    Many webhook providers provide an HMAC header. LemonSqueezy docs vary, so
    we accept header name 'X-LemonSqueezy-Signature' (common) and fall back to
    accepting if no secret is configured (but we log a warning upstream).
    """
    if not LEMONSQUEEZY_WEBHOOK_SECRET:
        # No secret configured — cannot verify, let caller decide.
        return True
    if not header_signature:
        return False

    try:
        computed = hmac.new(LEMONSQUEEZY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
        # Some providers include timestamp and signature or multiple signatures.
        # We simply compare hex digests; if the header contains multiple parts
        # or prefixed text, try to find the digest substring.
        return hmac.compare_digest(computed, header_signature) or (header_signature.find(computed) != -1)
    except Exception:
        return False
