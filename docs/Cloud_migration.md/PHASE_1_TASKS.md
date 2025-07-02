# Phase 1: Core Infrastructure Setup - Task List

**Duration**: 1 week  
**Dependencies**: None

## Task Execution Order

### 1. Railway Backend Service Setup
**Dependencies**: None  
**Estimated Time**: 1-2 days

1.1. **Create Railway Account & Project**
   - Sign up for Railway account
   - Create new project for Narratix 2.0
   - Connect GitHub repository to Railway

1.2. **Configure Railway Environment**
   - Set up environment variables (ANTHROPIC_API_KEY, HUME_API_KEY, REPLICATE_API_TOKEN)
   - Configure Railway deployment settings
   - Set up custom domain (if needed)

1.3. **Deploy FastAPI Application** ✅ **COMPLETED**
   - ✅ Create Dockerfile for containerization
   - ✅ Configure uvicorn settings for production (4 workers, production logging)
   - ✅ Test deployment and verify health endpoints (/health, /health/detailed, /health/ready)
   - ✅ Set up auto-deploy from GitHub main branch (railway.toml configured)

### 2. Neon PostgreSQL Database Setup
**Dependencies**: Railway project created  
**Estimated Time**: 1 day

2.1. **Create Neon Account & Databases** ✅ **COMPLETED**
   - ✅ Sign up for Neon PostgreSQL
   - ✅ Create midsummerr project (main branch = production)
   - ✅ Create staging branch (`development`)
   - ✅ Get connection strings for both branches
   - ✅ Configure branch-specific connection strings

2.2. **Configure Database Connections** 🔄 **IN PROGRESS**
   - 🔄 Test connection strings locally
   - 🔄 Add DATABASE_URL environment variables to Railway
   - 🔄 Set up connection pooling parameters
   - 🔄 Test database connectivity from Railway
   - 🔄 Verify SSL connections working

### 3. Cloudflare R2 Storage Setup
**Dependencies**: None (can run parallel with Railway/Neon)  
**Estimated Time**: 1 day

3.1. **Create Cloudflare Account & R2 Service**
   - ✅ Sign up for Cloudflare account
   - ✅ Enable R2 object storage
   - ✅ Create staging bucket (`narratix-staging`)
   - ✅ Create production bucket (`narratix-production`)

3.2. **Configure Access & Security**
   - Generate R2 API tokens
   - Set up IAM policies for bucket access
   - Configure CORS policies for web access
   - Add R2 credentials to Railway environment variables

3.3. **Test Basic Operations**
   - Implement basic upload/download functionality
   - Test file operations from Railway environment
   - Verify CORS configuration with test uploads

### 4. Domain & SSL Configuration
**Dependencies**: Railway deployment working  
**Estimated Time**: 0.5 days

4.1. **Domain Setup** (if using custom domain)
   - Configure custom domain in Railway
   - Update DNS records
   - Verify SSL certificate installation

4.2. **CORS Configuration**
   - Update CORS policies for Vercel domain
   - Test cross-origin requests from landing page
   - Verify preflight requests working

### 5. Integration Testing & Validation
**Dependencies**: All above tasks complete  
**Estimated Time**: 0.5 days

5.1. **End-to-End Connectivity Tests**
   - Test all service integrations
   - Verify environment variables loaded correctly
   - Test database connections and basic queries
   - Test file upload/download to R2

5.2. **External API Integration Tests**
   - Test Anthropic Claude API connectivity
   - Test Hume AI API connectivity
   - Test Replicate API connectivity
   - Verify all API keys working in production environment

## Success Criteria Checklist

- [ ] Railway backend responds to health checks from public URL
- [ ] Database connections successful from Railway environment
- [ ] File upload/download working with R2 from Railway
- [ ] CORS configured for web access from Vercel domain
- [ ] All external API integrations working
- [ ] Auto-deploy from GitHub configured and working
- [ ] Environment variables properly configured and accessible
- [ ] SSL certificates installed and working

## Critical Dependencies

### Technical Prerequisites
- GitHub repository access
- Valid API keys for all external services
- Domain name (if using custom domain)

### Account Requirements
- Railway account with billing configured
- Neon PostgreSQL account
- Cloudflare account with R2 enabled
- All external API service accounts (Anthropic, Hume, Replicate)

### Development Requirements
- Docker installed locally for testing containerization
- Access to current codebase and environment variables
- Ability to test deployments before production


## Phase 1 Completion Criteria

All tasks must be completed and verified before proceeding to Phase 2. The infrastructure should be stable and all services accessible from public URLs.