#!/usr/bin/env python3
"""
Test script for Neon PostgreSQL database connection.
Run this after configuring DATABASE_URL environment variable.
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Load environment variables
load_dotenv()

def test_neon_connection():
    """Test connection to Neon PostgreSQL database."""
    from db.database import test_database_connection, health_check
    
    print("Testing Neon PostgreSQL Connection...")
    print("=" * 50)
    
    # Get DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        return False
    
    if database_url.startswith("sqlite"):
        print("⚠️  WARNING: Currently using SQLite, not PostgreSQL")
        print(f"   DATABASE_URL: {database_url}")
        print("   Please set DATABASE_URL to your Neon PostgreSQL connection string")
        return False
    
    print(f"🔗 Database URL: {database_url.split('@')[-1]}")  # Hide credentials
    
    # Test basic connection
    print("\n1. Testing basic connection...")
    connection_result = test_database_connection()
    
    if connection_result["connected"]:
        print("✅ Database connection successful!")
        print(f"   Test query result: {connection_result['test_query_result']}")
    else:
        print("❌ Database connection failed!")
        print(f"   Error: {connection_result['error']}")
        return False
    
    # Test health check
    print("\n2. Running database health check...")
    health_result = health_check()
    
    if health_result["healthy"]:
        print("✅ Database health check passed!")
    else:
        print("⚠️  Database health check has warnings")
    
    print(f"   Pool utilization: {health_result['pool_utilization_percent']}%")
    
    if health_result["recommendations"]:
        print("   Recommendations:")
        for rec in health_result["recommendations"]:
            print(f"   - {rec}")
    
    # Test table creation (simulated)
    print("\n3. Testing table operations...")
    try:
        from db.database import engine, Base
        from sqlalchemy import text
        
        # Test creating a simple table
        with engine.connect() as conn:
            # Check if we can run PostgreSQL-specific queries
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL version: {version}")
            
            # Test transaction capability
            with conn.begin():
                conn.execute(text("SELECT NOW()"))
            print("✅ Transaction support working")
            
    except Exception as e:
        print(f"❌ Table operation test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All Neon PostgreSQL tests passed!")
    print("\nNext steps:")
    print("1. Test staging branch connection")
    print("2. Deploy production branch config to Railway")
    print("3. Test from Railway environment")
    print("4. Run database migrations on both branches")
    
    return True

if __name__ == "__main__":
    success = test_neon_connection()
    sys.exit(0 if success else 1) 