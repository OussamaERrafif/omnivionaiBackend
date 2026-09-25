# 🔧 Bug Fix: TypeError in Privacy Endpoints

## Problem
```
TypeError: get_user_subscription() missing 1 required positional argument: 'request'
```

## Root Cause
The `@require_auth` decorator expects the function parameter to be named **`request`** (not `req`).

Looking at the decorator implementation in `auth_utils.py`:
```python
@require_auth
async def example_endpoint(request: Request):  # ✅ Must be 'request'
    user_id = request.state.user_id
```

## Fix Applied ✅

Changed all new endpoint parameters from `req` to `request`:

### 1. `/api/subscription` endpoint
```python
# ❌ Before:
async def get_user_subscription(req: Request):
    user_id = req.state.user_id

# ✅ After:
async def get_user_subscription(request: Request):
    user_id = request.state.user_id
```

### 2. `/api/usage-logs` endpoint
```python
# ❌ Before:
async def get_usage_logs(req: Request, limit: int = 20):
    user_id = req.state.user_id

# ✅ After:
async def get_usage_logs(request: Request, limit: int = 20):
    user_id = request.state.user_id
```

## Next Steps

### 1. Restart Backend Server
```powershell
# Stop current server (Ctrl+C if running)
# Then restart:
cd backend
python app.py
```

### 2. Test the Endpoints
```powershell
# Test public endpoint (no auth):
curl http://localhost:8000/api/plan-features

# Test with authentication (get JWT token first):
# Sign in to your app, then get token from browser DevTools
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/api/subscription
```

### 3. Verify in Frontend
- Refresh your frontend app
- The `getUserSubscription()` function should now work
- Check browser DevTools Console for any remaining errors

## Files Modified
- `backend/app.py` - Fixed parameter names in 2 endpoints

---

**Status**: ✅ Fixed and ready to test
**Date**: November 1, 2025



