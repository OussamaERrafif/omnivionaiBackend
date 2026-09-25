# 🔑 How to Fix JWT Authentication

## Problem
```
Invalid JWT token: Signature verification failed
INFO: 127.0.0.1:56706 - "GET /api/subscription HTTP/1.1" 401 Unauthorized
```

## Root Cause
The `SUPABASE_JWT_SECRET` in your backend `.env` file is set to `kawazaki`, but it needs to be your **actual Supabase JWT secret**.

## Solution: Get Your JWT Secret from Supabase

### Option 1: From Supabase Dashboard (Recommended)

1. **Go to your Supabase project**: https://supabase.com/dashboard
2. **Navigate to**: Settings → API
3. **Find**: "JWT Secret" section
4. **Copy** the JWT Secret value
5. **Update** `backend/.env`:

```env
# Replace this:
SUPABASE_JWT_SECRET = kawazaki

# With your actual JWT secret:
SUPABASE_JWT_SECRET=your-actual-jwt-secret-from-supabase-dashboard
```

### Option 2: From Frontend .env.local

Your frontend already has the correct Supabase URL. The JWT secret is the **secret key** used to sign tokens, which you can find in the Supabase dashboard.

## Quick Fix (Temporary - Development Only)

For **development/testing only**, you can temporarily bypass JWT verification:

### Update `backend/auth_utils.py`:

**⚠️ WARNING: This is INSECURE and should ONLY be used for local testing!**

```python
def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token from Supabase Auth"""
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        # 🔧 TEMPORARY FIX: Decode without verification for testing
        # ⚠️ NEVER USE IN PRODUCTION!
        payload = jwt.decode(
            token,
            options={"verify_signature": False}  # ⚠️ INSECURE!
        )
        
        return payload
        
    except Exception as e:
        logger.error(f"Error decoding JWT token: {str(e)}")
        return None
```

## Recommended Fix (Production-Ready)

### 1. Get JWT Secret from Supabase Dashboard

```
Supabase Dashboard → Your Project → Settings → API → JWT Secret
```

### 2. Update backend/.env

```env
# Supabase Configuration
SUPABASE_URL=https://aufshhpzorebyibhmkxc.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-actual-jwt-secret-here  # ← UPDATE THIS!
```

### 3. Restart Backend Server

```powershell
cd backend
python app.py
```

## How to Find Your JWT Secret

### Via Supabase Dashboard:

1. Open: https://supabase.com/dashboard/project/aufshhpzorebyibhmkxc/settings/api
   (Replace `aufshhpzorebyibhmkxc` with your project ref)

2. Look for **"JWT Settings"** section

3. Copy the **"JWT Secret"** value

4. It looks like: `super-secret-jwt-token-with-at-least-32-characters-long`

### Common Confusion:

| What | Where | Purpose |
|------|-------|---------|
| **Anon Key** | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Client-side auth (frontend) |
| **Service Role Key** | `SUPABASE_SERVICE_ROLE_KEY` | Server-side admin access (backend) |
| **JWT Secret** ⭐ | `SUPABASE_JWT_SECRET` | **Sign/verify JWT tokens (backend)** |

The JWT Secret is used to **verify** that tokens sent from the frontend are legitimate.

## Test After Fix

```powershell
# Restart backend
cd backend
python app.py

# In browser, refresh your app
# Check DevTools console - should see successful API calls
```

## Expected Result

**Before:**
```
❌ Invalid JWT token: Signature verification failed
❌ 401 Unauthorized
```

**After:**
```
✅ INFO: 127.0.0.1:56706 - "GET /api/subscription HTTP/1.1" 200 OK
✅ Successfully fetched subscription data
```

---

**Status**: ⚠️ Waiting for JWT Secret from Supabase Dashboard
**Priority**: 🔴 Critical - Required for authentication to work
