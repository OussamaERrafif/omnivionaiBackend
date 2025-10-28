#!/usr/bin/env python3
"""
Backend Environment Security Validator

Purpose: Validate backend environment configuration for security compliance
Usage: python validate_backend_security.py
"""

import os
import sys
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SecurityValidator:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
        
    def validate_all(self) -> bool:
        """Run all validation checks"""
        print("🔒 Backend Security Validation")
        print("=" * 70)
        
        self.check_supabase_config()
        self.check_api_keys()
        self.check_security_settings()
        self.check_dangerous_settings()
        
        self.print_results()
        
        return len(self.errors) == 0
    
    def check_supabase_config(self):
        """Validate Supabase configuration"""
        print("\n📊 Checking Supabase Configuration...")
        
        # Check URL
        url = os.getenv("SUPABASE_URL")
        if not url:
            self.errors.append("SUPABASE_URL is missing")
        elif not url.startswith("https://"):
            self.errors.append("SUPABASE_URL must use HTTPS")
        else:
            self.passed.append("SUPABASE_URL configured correctly")
        
        # Check SERVICE_ROLE key
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not service_key:
            self.errors.append("SUPABASE_SERVICE_ROLE_KEY is missing")
        elif service_key.startswith("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"):
            # Valid JWT format
            if "service_role" in service_key or len(service_key) > 200:
                self.passed.append("SUPABASE_SERVICE_ROLE_KEY configured")
            else:
                self.warnings.append("SERVICE_ROLE_KEY format looks unusual")
        else:
            self.errors.append("SUPABASE_SERVICE_ROLE_KEY invalid format")
        
        # Check for ANON key in backend (DANGER!)
        anon_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        if anon_key:
            self.errors.append("❌ SECURITY RISK: ANON KEY found in backend .env! Remove it!")
    
    def check_api_keys(self):
        """Validate API keys"""
        print("\n🔑 Checking API Keys...")
        
        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            self.warnings.append("OPENAI_API_KEY missing (required for AI features)")
        elif openai_key.startswith("sk-"):
            self.passed.append("OPENAI_API_KEY configured")
        else:
            self.errors.append("OPENAI_API_KEY invalid format")
        
        # Lemon Squeezy
        ls_key = os.getenv("LEMON_SQUEEZY_API_KEY")
        if not ls_key:
            self.warnings.append("LEMON_SQUEEZY_API_KEY missing (required for billing)")
        else:
            self.passed.append("LEMON_SQUEEZY_API_KEY configured")
        
        ls_secret = os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET")
        if not ls_secret:
            self.warnings.append("LEMON_SQUEEZY_WEBHOOK_SECRET missing")
        elif ls_secret.startswith("whsec_"):
            self.passed.append("LEMON_SQUEEZY_WEBHOOK_SECRET configured")
        else:
            self.warnings.append("LEMON_SQUEEZY_WEBHOOK_SECRET format unusual")
    
    def check_security_settings(self):
        """Validate security settings"""
        print("\n🛡️ Checking Security Settings...")
        
        # Environment
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production":
            self.passed.append("Running in PRODUCTION mode")
            
            # Production-specific checks
            debug = os.getenv("DEBUG", "False").lower()
            if debug == "true":
                self.errors.append("❌ DEBUG=True in production! Set to False!")
            
            reload = os.getenv("RELOAD", "False").lower()
            if reload == "true":
                self.warnings.append("RELOAD=True in production (not recommended)")
        else:
            self.passed.append(f"Running in {env.upper()} mode")
        
        # CORS
        cors = os.getenv("CORS_ORIGINS")
        if not cors:
            self.warnings.append("CORS_ORIGINS not set (will allow all origins)")
        elif "*" in cors:
            self.warnings.append("CORS allows all origins (*) - not secure for production")
        else:
            self.passed.append("CORS_ORIGINS configured")
    
    def check_dangerous_settings(self):
        """Check for dangerous configurations"""
        print("\n⚠️ Checking for Security Risks...")
        
        # Check if file contains example values
        with open('.env', 'r') as f:
            content = f.read()
            
            if 'YOUR_SERVICE_ROLE_KEY_HERE' in content:
                self.errors.append("❌ .env still contains example values!")
            
            if 'your-project-id' in content:
                self.errors.append("❌ .env contains placeholder URLs!")
            
            # Check for hardcoded secrets in code (should never happen)
            if 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSI' in content:
                self.warnings.append("Possible hardcoded JWT in .env (verify it's your key)")
    
    def print_results(self):
        """Print validation results"""
        print("\n" + "=" * 70)
        print("📋 VALIDATION RESULTS")
        print("=" * 70)
        
        if self.passed:
            print(f"\n✅ PASSED ({len(self.passed)}):")
            for item in self.passed:
                print(f"  ✓ {item}")
        
        if self.warnings:
            print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
            for item in self.warnings:
                print(f"  ! {item}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for item in self.errors:
                print(f"  ✗ {item}")
        
        print("\n" + "=" * 70)
        
        if self.errors:
            print("❌ VALIDATION FAILED - Fix errors before deploying!")
            print("=" * 70)
            return False
        elif self.warnings:
            print("⚠️ VALIDATION PASSED WITH WARNINGS - Review before deploying")
            print("=" * 70)
            return True
        else:
            print("✅ VALIDATION PASSED - Backend security looks good!")
            print("=" * 70)
            return True

def main():
    """Main entry point"""
    # Check if .env exists
    if not os.path.exists('.env'):
        print("❌ ERROR: .env file not found!")
        print("Create .env file using .env.example as template")
        sys.exit(1)
    
    validator = SecurityValidator()
    success = validator.validate_all()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
