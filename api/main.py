from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os
import time
from typing import Dict, List
from datetime import datetime, timedelta

from .endpoints import text, character, audio, sound_effects, audio_analysis, background_music, export_audio, text_analysis, replicate_webhook
from db.database import engine, Base
from utils.config import settings
from utils.logging import SessionLogger, get_logger
import utils.http_client

# Initialize logger
logger = get_logger(__name__)

# Start API session only if no session exists (preserve test session when under pytest)
existing_session = SessionLogger.get_current_session()
if not existing_session:
    api_session_id = SessionLogger.start_session("api_server")
else:
    api_session_id = existing_session

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Narratix API",
    description="API for Narratix text-to-audio conversion",
    version="2.0.0"
)

# Webhook monitoring state
webhook_failures: Dict[str, List[datetime]] = {}

class WebhookMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor webhook failures and performance."""
    
    async def dispatch(self, request: Request, call_next):
        # Only monitor webhook endpoints
        if not request.url.path.startswith("/api/replicate-webhook/"):
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log webhook processing time
            processing_time = time.time() - start_time
            logger.info(f"Webhook processed in {processing_time:.3f}s: {request.url.path}")
            
            # Monitor failures if enabled
            if settings.WEBHOOK_MONITORING_ENABLED and response.status_code >= 400:
                await self._record_webhook_failure(request.url.path, response.status_code)
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Webhook error after {processing_time:.3f}s: {request.url.path} - {str(e)}")
            
            # Record failure if monitoring enabled
            if settings.WEBHOOK_MONITORING_ENABLED:
                await self._record_webhook_failure(request.url.path, 500)
            
            raise
    
    async def _record_webhook_failure(self, path: str, status_code: int):
        """Record webhook failure for monitoring."""
        now = datetime.now()
        
        # Initialize failure list for this path if needed
        if path not in webhook_failures:
            webhook_failures[path] = []
        
        # Add failure timestamp
        webhook_failures[path].append(now)
        
        # Clean up old failures (keep only last hour)
        cutoff = now - timedelta(hours=1)
        webhook_failures[path] = [ts for ts in webhook_failures[path] if ts > cutoff]
        
        # Check if we've exceeded the failure threshold
        failure_count = len(webhook_failures[path])
        if failure_count >= settings.WEBHOOK_FAILURE_ALERT_THRESHOLD:
            logger.error(f"WEBHOOK ALERT: {failure_count} failures in last hour for {path} (status: {status_code})")

# Add webhook monitoring middleware if enabled
if settings.WEBHOOK_MONITORING_ENABLED:
    app.add_middleware(WebhookMonitoringMiddleware)
    logger.info("Webhook monitoring middleware enabled")

# CORS middleware with production-aware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log CORS configuration
if settings.is_production():
    logger.info(f"Production CORS origins: {settings.CORS_ORIGINS}")
else:
    logger.info("Development CORS: allowing all origins")

# Include routers
app.include_router(text.router)
app.include_router(character.router)
app.include_router(audio.router)
app.include_router(audio_analysis.router)
app.include_router(sound_effects.router)
app.include_router(background_music.router)
app.include_router(export_audio.router)
app.include_router(text_analysis.router)
app.include_router(replicate_webhook.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to Narratix API"}

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "narratix-api", "version": "2.0.0"}

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service dependencies"""
    health_status = {
        "status": "healthy",
        "service": "narratix-api", 
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check database connection
    try:
        from db.database import get_db
        db = next(get_db())
        # Simple query to test connection
        db.execute("SELECT 1")
        health_status["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check API keys presence
    api_keys_status = {
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "hume": bool(settings.HUME_API_KEY), 
        "replicate": bool(settings.REPLICATE_API_TOKEN)
    }
    
    if all(api_keys_status.values()):
        health_status["checks"]["api_keys"] = {"status": "healthy"}
    else:
        health_status["checks"]["api_keys"] = {
            "status": "unhealthy", 
            "missing_keys": [k for k, v in api_keys_status.items() if not v]
        }
        health_status["status"] = "unhealthy"
    
    return health_status

@app.get("/health/ready")
async def readiness_check():
    """Kubernetes-style readiness probe"""
    try:
        # Quick checks for service readiness
        from db.database import get_db
        db = next(get_db())
        db.execute("SELECT 1")
        
        # Check critical environment variables
        if not all([settings.ANTHROPIC_API_KEY, settings.HUME_API_KEY, settings.REPLICATE_API_TOKEN]):
            return {"status": "not_ready", "reason": "missing_api_keys"}, 503
            
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "reason": str(e)}, 503

@app.get("/webhook-status")
async def webhook_status():
    """Get webhook monitoring status."""
    if not settings.WEBHOOK_MONITORING_ENABLED:
        return {"monitoring": "disabled"}
    
    # Clean up old failures
    now = datetime.now()
    cutoff = now - timedelta(hours=1)
    
    status = {
        "monitoring": "enabled",
        "failure_threshold": settings.WEBHOOK_FAILURE_ALERT_THRESHOLD,
        "webhook_timeout": settings.WEBHOOK_TIMEOUT_SECONDS,
        "paths": {}
    }
    
    for path, failures in webhook_failures.items():
        # Clean up old failures
        recent_failures = [ts for ts in failures if ts > cutoff]
        webhook_failures[path] = recent_failures
        
        status["paths"][path] = {
            "failures_last_hour": len(recent_failures),
            "status": "alert" if len(recent_failures) >= settings.WEBHOOK_FAILURE_ALERT_THRESHOLD else "ok",
            "last_failure": recent_failures[-1].isoformat() if recent_failures else None
        }
    
    return status