from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Import settings for centralized configuration
from utils.config import settings

DATABASE_URL = settings.DATABASE_URL

# Database connection pooling configuration (now from settings)
DB_POOL_SIZE = settings.DB_POOL_SIZE
DB_MAX_OVERFLOW = settings.DB_MAX_OVERFLOW
DB_POOL_TIMEOUT = settings.DB_POOL_TIMEOUT
DB_POOL_RECYCLE = settings.DB_POOL_RECYCLE
DB_POOL_PRE_PING = settings.DB_POOL_PRE_PING
DB_ECHO = settings.DB_ECHO

# Enhanced database configuration for parallel processing
if DATABASE_URL.startswith("sqlite"):
    # For SQLite, add connect_args to disable same-thread check and enable WAL mode for better concurrency
    engine = create_engine(
        DATABASE_URL, 
        connect_args={
            "check_same_thread": False,
            "timeout": 20,  # 20 second timeout for SQLite connections
            # Enable WAL mode for better concurrency (Write-Ahead Logging)
            "isolation_level": None,  # Let SQLite manage isolation
        },
        poolclass=StaticPool,  # SQLite works better with StaticPool for file-based databases
        echo=DB_ECHO
    )
    
    # Configure SQLite for better concurrency
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Configure SQLite for better concurrent access."""
        cursor = dbapi_connection.cursor()
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        # Reduce lock timeout
        cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys=ON")
        # Optimize cache size
        cursor.execute("PRAGMA cache_size=10000")  # 10MB cache
        # Set synchronous mode for better performance with WAL
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
        
else:
    # For PostgreSQL/MySQL with full parallel processing support
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,        # Use QueuePool for PostgreSQL/MySQL
        pool_size=DB_POOL_SIZE,     # Base connection pool size
        max_overflow=DB_MAX_OVERFLOW, # Additional connections beyond pool_size
        pool_timeout=DB_POOL_TIMEOUT, # Timeout to get connection from pool
        pool_pre_ping=DB_POOL_PRE_PING, # Verify connection health before use
        pool_recycle=DB_POOL_RECYCLE,   # Refresh connections periodically
        echo=DB_ECHO,               # Log SQL statements if enabled
        # Additional PostgreSQL optimizations  
        # Note: Neon connection pooler doesn't support statement_timeout parameter
        connect_args={
            "options": "-c statement_timeout=300000"  # 5 minute statement timeout
        } if "postgresql" in DATABASE_URL and "neon.tech" not in DATABASE_URL else {}
    )

# Create session factory with optimized settings
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False,  # Manual flushing for better control
    bind=engine,
    # Expire on commit to avoid stale data issues
    expire_on_commit=True
)

Base = declarative_base()

def get_db():
    """
    Dependency function to get database session.
    Used by FastAPI Depends() for automatic session management.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_connection_pool_status():
    """
    Get current connection pool status for monitoring and debugging.
    
    Returns:
        Dictionary with pool statistics
    """
    pool = engine.pool
    
    status = {
        "pool_size": pool.size(),
        "checked_in_connections": pool.checkedin(),
        "checked_out_connections": pool.checkedout(),
        "overflow_connections": pool.overflow(),
        "invalid_connections": getattr(pool, 'invalid', lambda: 0)(),  # Some pool types don't have invalid()
        "total_connections": pool.size() + pool.overflow(),
    }
    
    # Add pool configuration info
    status.update({
        "configured_pool_size": DB_POOL_SIZE,
        "configured_max_overflow": DB_MAX_OVERFLOW,
        "configured_timeout": DB_POOL_TIMEOUT,
        "configured_recycle": DB_POOL_RECYCLE,
        "database_type": "sqlite" if DATABASE_URL.startswith("sqlite") else "postgresql/mysql"
    })
    
    return status

def log_connection_pool_status():
    """Log current connection pool status for debugging."""
    status = get_connection_pool_status()
    logging.info(f"Database Connection Pool Status: {status}")

def test_database_connection():
    """
    Test database connection and return connection info.
    
    Returns:
        Dictionary with connection test results
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            
            return {
                "connected": True,
                "database_url": DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL,  # Hide credentials
                "pool_status": get_connection_pool_status(),
                "test_query_result": row[0] if row else None
            }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "database_url": DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL,
        }

# Health check function for production monitoring
def health_check():
    """
    Comprehensive database health check for production monitoring.
    
    Returns:
        Dictionary with health status and metrics
    """
    connection_test = test_database_connection()
    pool_status = get_connection_pool_status()
    
    # Calculate pool utilization
    total_capacity = pool_status["configured_pool_size"] + pool_status["configured_max_overflow"]
    current_usage = pool_status["checked_out_connections"]
    utilization_percent = (current_usage / total_capacity * 100) if total_capacity > 0 else 0
    
    # Determine health status
    is_healthy = (
        connection_test["connected"] and
        utilization_percent < 90 and  # Pool not overloaded
        pool_status["invalid_connections"] == 0  # No invalid connections
    )
    
    return {
        "healthy": is_healthy,
        "connection_test": connection_test,
        "pool_status": pool_status,
        "pool_utilization_percent": round(utilization_percent, 2),
        "recommendations": _get_health_recommendations(pool_status, utilization_percent)
    }

def _get_health_recommendations(pool_status, utilization_percent):
    """Generate health recommendations based on current status."""
    recommendations = []
    
    if utilization_percent > 80:
        recommendations.append("Consider increasing DB_POOL_SIZE or DB_MAX_OVERFLOW")
    
    if pool_status["invalid_connections"] > 0:
        recommendations.append("Invalid connections detected - check network stability")
    
    if pool_status["overflow_connections"] > pool_status["configured_pool_size"]:
        recommendations.append("Using overflow connections - consider increasing base pool size")
    
    return recommendations