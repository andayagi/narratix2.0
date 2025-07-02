# Narratix API - Railway Deployment Guide

## Production Deployment Setup

### Prerequisites
- Railway account with billing configured
- GitHub repository connected to Railway
- Environment variables ready (see below)

### Step 1: Connect Repository to Railway

1. **Create Railway Project**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login to Railway
   railway login
   
   # Create new project
   railway init
   ```

2. **Connect GitHub Repository**
   - Go to Railway dashboard
   - Select "Deploy from GitHub repo"
   - Choose your Narratix2.0 repository
   - Select the main branch

### Step 2: Configure Environment Variables

Set these environment variables in Railway dashboard:

**Required API Keys:**
```
ANTHROPIC_API_KEY=your_anthropic_key
HUME_API_KEY=your_hume_key  
REPLICATE_API_TOKEN=your_replicate_token
```

**Production Configuration:**
```
ENVIRONMENT=production
BASE_URL=https://your-railway-domain.railway.app
```

**Database Configuration (when ready):**
```
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

**Storage Configuration (when ready):**
```
R2_ACCOUNT_ID=your_r2_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET_NAME=narratix-production
```

**Optional Monitoring:**
```
WEBHOOK_MONITORING_ENABLED=true
WEBHOOK_FAILURE_ALERT_THRESHOLD=5
WEBHOOK_TIMEOUT_SECONDS=30
```

### Step 3: Deploy Application

Railway will automatically detect the `nixpacks.toml` configuration and:
- Use Python buildpack
- Install dependencies from `requirements.txt`
- Run production uvicorn server with 4 workers
- Expose health check on `/health`

### Step 4: Verify Deployment

1. **Check Health Endpoints**
   ```bash
   curl https://your-app.railway.app/health
   curl https://your-app.railway.app/health/detailed
   curl https://your-app.railway.app/health/ready
   ```

2. **Verify Production Configuration**
   ```bash
   curl https://your-app.railway.app/health/detailed
   # Should show "environment": "production"
   ```

3. **Test API Endpoints**
   ```bash
   curl https://your-app.railway.app/
   # Should return: {"message": "Welcome to Narratix API"}
   ```

### Step 5: Enable Auto-Deploy

Railway automatically deploys from the main branch when:
- Code is pushed to GitHub main branch
- The `railway.toml` configuration is detected
- Health checks pass during deployment

### Deployment Configuration Files

- **`Dockerfile`**: Production container configuration
- **`nixpacks.toml`**: Railway-specific build configuration  
- **`railway.toml`**: Railway deployment settings
- **`.dockerignore`**: Files excluded from container build

### Production Settings Applied

- **4 uvicorn workers** for better performance
- **Production logging** with access logs enabled
- **Health checks** for container monitoring
- **Non-root user** for security
- **Environment-based configuration** 
- **Optimized Docker layers** for faster builds

### Monitoring & Health Checks

Railway will:
- Monitor `/health` endpoint every 30 seconds
- Restart service if health checks fail
- Provide logs and metrics in dashboard
- Auto-scale based on traffic (if configured)

### Troubleshooting

**Common Issues:**

1. **Build Failures:**
   - Check `nixpacks.toml` syntax
   - Verify `requirements.txt` dependencies
   - Check build logs in Railway dashboard

2. **Health Check Failures:**
   - Verify database connections
   - Check API key configuration
   - Review application logs

3. **Environment Variable Issues:**
   - Ensure all required variables are set
   - Check variable names match exactly
   - Verify no trailing spaces in values

**Useful Commands:**
```bash
# View logs
railway logs

# Open deployment URL
railway open

# Check environment variables
railway variables

# Deploy specific branch
railway up
```

### Next Steps

After successful deployment:
1. Configure database connection (Phase 2)
2. Set up file storage with R2 (Phase 2)  
3. Configure custom domain (optional)
4. Set up monitoring and alerts
5. Configure backup and disaster recovery 