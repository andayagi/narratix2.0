#!/usr/bin/env python3
"""
Simple startup test to verify the application can initialize without errors.
Run this locally to debug startup issues before deploying to Railway.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported."""
    try:
        print("Testing imports...")
        
        # Test database imports
        from db.database import engine, Base
        print("✓ Database imports successful")
        
        # Test config
        from utils.config import settings
        print("✓ Config imports successful")
        
        # Test main app
        from api.main import app
        print("✓ FastAPI app imports successful")
        
        # Test critical services
        from services import text_analysis, voice_generation, speech_generation
        print("✓ Core services imports successful")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_database_connection():
    """Test database connection."""
    try:
        print("Testing database connection...")
        from db.database import test_database_connection
        result = test_database_connection()
        
        if result.get("connected"):
            print("✓ Database connection successful")
            return True
        else:
            print(f"✗ Database connection failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_app_startup():
    """Test that the FastAPI app can start."""
    try:
        print("Testing FastAPI app startup...")
        from api.main import app
        
        # Test that health endpoint exists
        routes = [route.path for route in app.routes]
        if "/health" in routes:
            print("✓ Health endpoint configured")
        else:
            print("✗ Health endpoint missing")
            return False
            
        print("✓ FastAPI app startup successful")
        return True
    except Exception as e:
        print(f"✗ App startup failed: {e}")
        return False

def main():
    """Run all startup tests."""
    print("=== Railway Deployment Startup Test ===\n")
    
    tests = [
        ("Import Test", test_imports),
        ("Database Test", test_database_connection),
        ("App Startup Test", test_app_startup)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        success = test_func()
        results.append((test_name, success))
    
    print("\n=== Test Results ===")
    all_passed = True
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n✅ All tests passed! App should deploy successfully to Railway.")
    else:
        print("\n❌ Some tests failed. Fix these issues before deploying to Railway.")
        sys.exit(1)

if __name__ == "__main__":
    main()