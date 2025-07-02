# Railway Deployment Guide

## Fixed Issues

### 1. Heavy ML Dependencies Removed
- Commented out PyTorch/WhisperX dependencies in requirements.txt
- Created requirements-production.txt without heavy ML packages
- Updated Dockerfile to use production requirements

### 2. Database Configuration
- Added PostgreSQL driver (psycopg2-binary) for production
- Database pooling configured for both SQLite (dev) and PostgreSQL (prod)

### 3. Environment Variables Required on Railway

Set these in Railway dashboard:

```bash
# Core API Keys (REQUIRED)
ANTHROPIC_API_KEY=your_anthropic_key
HUME_API_KEY=your_hume_key  
REPLICATE_API_TOKEN=your_replicate_token

# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/database

# Production Settings
ENVIRONMENT=production
BASE_URL=https://your-railway-domain.railway.app

# Optional Configuration
CORS_ORIGINS=https://your-frontend-domain.com
WEBHOOK_MONITORING_ENABLED=true
DB_ECHO=false
```

## Deployment Steps

1. **Push changes to GitHub**
2. **Set environment variables in Railway**
3. **Deploy will auto-trigger**
4. **Check health endpoints:**
   - `/health` - Basic health check
   - `/health/detailed` - Database and API key validation
   - `/health/ready` - Kubernetes-style readiness probe

## Post-Deployment Verification

```bash
# Test health endpoints
curl https://your-domain.railway.app/health
curl https://your-domain.railway.app/health/detailed

# Test basic API
curl https://your-domain.railway.app/
```

## Common Issues

1. **Build failures** - Usually missing environment variables
2. **Database connection** - Check DATABASE_URL format and network access
3. **API key issues** - Verify all required keys are set and valid

## Future: WhisperX Integration

When ready to add force alignment:
1. Uncomment WhisperX dependencies in requirements.txt
2. Update Dockerfile with additional system dependencies
3. Consider using Railway's larger instance types