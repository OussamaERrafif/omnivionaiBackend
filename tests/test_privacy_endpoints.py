"""
Test script for privacy-enhanced subscription endpoints

Usage:
    python test_privacy_endpoints.py

Requirements:
    - Backend server running on http://localhost:8000
    - Valid JWT token (get from Supabase auth)
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
JWT_TOKEN = ""  # ⚠️ Replace with valid JWT token from Supabase

def run_public_endpoints():
    """Test public endpoints (no auth required)"""
    print("\n=== Testing Public Endpoints ===\n")
    
    # Test: Get all plan features
    print("1. GET /api/plan-features")
    try:
        response = requests.get(f"{BASE_URL}/api/plan-features")
        print(f"   Status: {response.status_code}")
        if response.ok:
            data = response.json()
            print(f"   ✅ Success! Found {len(data)} plans")
        else:
            print(f"   ❌ Failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print()
    
    # Test: Get specific plan features
    for plan_type in ["free", "pro", "enterprise"]:
        print(f"2. GET /api/plan-features/{plan_type}")
        try:
            response = requests.get(f"{BASE_URL}/api/plan-features/{plan_type}")
            print(f"   Status: {response.status_code}")
            if response.ok:
                data = response.json()
                print(f"   ✅ Success! Plan: {data.get('plan_type', 'N/A')}")
            else:
                print(f"   ⚠️  Not found or error: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        print()

def run_authenticated_endpoints():
    """Test authenticated endpoints (requires JWT)"""
    print("\n=== Testing Authenticated Endpoints ===\n")
    
    if not JWT_TOKEN:
        print("❌ No JWT token provided! Set JWT_TOKEN variable in script.")
        print("   Get token from Supabase:")
        print("   1. Sign in to your app")
        print("   2. Open DevTools → Application → Local Storage")
        print("   3. Find 'sb-<project>-auth-token' → copy access_token")
        return
    
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
    
    # Test: Get user subscription
    print("1. GET /api/subscription")
    try:
        response = requests.get(f"{BASE_URL}/api/subscription", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.ok:
            data = response.json()
            print(f"   ✅ Success! Plan: {data.get('plan_type', 'N/A')}")
            print(f"   Searches remaining: {data.get('searches_remaining', 'N/A')}")
        else:
            print(f"   ❌ Failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print()
    
    # Test: Get usage logs
    print("2. GET /api/usage-logs?limit=5")
    try:
        response = requests.get(f"{BASE_URL}/api/usage-logs?limit=5", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.ok:
            data = response.json()
            print(f"   ✅ Success! Found {len(data)} usage logs")
        else:
            print(f"   ❌ Failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

def run_health_check():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===\n")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"GET /health - Status: {response.status_code}")
        if response.ok:
            print(f"✅ Backend is healthy!")
            print(f"   {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ Backend health check failed")
    except Exception as e:
        print(f"❌ Cannot connect to backend: {str(e)}")
        print(f"\n⚠️  Make sure backend is running:")
        print(f"   cd backend")
        print(f"   python app.py")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("Privacy-Enhanced Endpoints Test Suite")
    print("=" * 60)
    
    # Test health first
    run_health_check()
    
    # Test public endpoints
    run_public_endpoints()
    
    # Test authenticated endpoints
    run_authenticated_endpoints()
    
    print("\n" + "=" * 60)
    print("Test Suite Complete")
    print("=" * 60)
    
    if not JWT_TOKEN:
        print("\n⚠️  To test authenticated endpoints:")
        print("   1. Get JWT token from Supabase (see instructions above)")
        print("   2. Set JWT_TOKEN variable in this script")
        print("   3. Run again: python test_privacy_endpoints.py")
