# Narratix 2.0 Cloud Migration Project

## Project Overview

### Objective
Migrate Narratix 2.0 from local development to production-ready cloud infrastructure, enabling web demo integration with the Vercel-hosted landing page.

### Tech Stack Decisions
- **Backend Hosting**: Railway (containerized FastAPI deployment)
- **Database**: Neon PostgreSQL (managed, scalable)
- **Audio Storage**: Cloudflare R2 (S3-compatible object storage)
- **Job Tracking**: Database-only approach (no Redis/Celery for cost optimization)
- **CI/CD**: GitHub Actions with Railway auto-deploy

### Success Criteria
- [ ] Backend accessible via public API endpoints
- [ ] Web demo can process text and return audio within 5 minutes
- [ ] Staging/production environments properly separated
- [ ] Audio files stored in cloud with proper cleanup
- [ ] Cost under $20/month for MVP phase

### Timeline
**Total Duration**: 4-6 weeks
**Go-Live Target**: [To be determined]

---

## Phase 1: Core Infrastructure Setup
**Duration**: 1 week  
**Dependencies**: None

### Objectives
- Set up basic cloud services and connectivity
- Establish development workflow
- Validate service integrations

### Deliverables
1. **Railway Backend Service**
   - FastAPI application deployed and accessible
   - Environment variables configured
   - Health check endpoints working
   - Auto-deploy from GitHub configured

2. **Neon PostgreSQL Database**
   - Production and staging databases created
   - Connection strings configured
   - Basic connectivity verified
   - Connection pooling configured

3. **Cloudflare R2 Storage**
   - Buckets created (staging/production)
   - API keys and access configured
   - Basic upload/download functionality tested
   - CORS policies configured for web access

4. **Domain & SSL**
   - Custom domain configured (if needed)
   - SSL certificates installed
   - CORS policies updated for Vercel domain

### Technical Requirements
- Railway project with environment variables
- Neon database instances (staging/production)
- Cloudflare R2 buckets with proper IAM policies
- GitHub repository secrets configured

### Success Criteria
- [ ] Backend responds to health checks from public URL
- [ ] Database connections successful from Railway
- [ ] File upload/download working with R2
- [ ] CORS configured for web access

---

## Phase 2: Database Migration & Job Tracking
**Duration**: 1 week  
**Dependencies**: Phase 1 complete

### Objectives
- Migrate from SQLite to PostgreSQL
- Implement database-based job tracking system
- Update data models for cloud storage

### Deliverables
1. **Database Schema Migration**
   - Convert SQLite schema to PostgreSQL
   - Run Alembic migrations on cloud database
   - Update connection strings and pooling
   - Test data integrity and relationships

2. **Job Tracking System**
   - New `JobStatus` table and model
   - Job creation, update, and status endpoints
   - Progress tracking (0-100%) functionality
   - Error handling and logging

3. **Audio Storage Model Updates**
   - Remove base64 audio fields
   - Add cloud storage URL fields
   - Add audio metadata (duration, size, format)
   - Update CRUD operations for cloud storage

4. **Database Performance Optimization**
   - Indexes on frequently queried fields
   - Connection pooling configuration
   - Query optimization for job status checks

### Technical Requirements
- PostgreSQL-compatible SQL queries
- Alembic migration scripts
- New Pydantic schemas for job tracking
- Updated service layer methods

### Success Criteria
- [ ] All existing functionality works with PostgreSQL
- [ ] Job tracking system operational
- [ ] Audio metadata properly stored
- [ ] Database performance acceptable (< 100ms queries)

---

## Phase 3: Audio Storage Migration
**Duration**: 1-2 weeks  
**Dependencies**: Phase 2 complete

### Objectives
- Replace in-memory/base64 audio storage with cloud storage
- Implement proper audio file lifecycle management
- Optimize audio processing pipeline for cloud

### Deliverables
1. **Cloud Storage Integration**
   - S3-compatible client for R2 operations
   - Upload/download methods for all audio types
   - Presigned URL generation for secure access
   - File naming conventions and organization

2. **Audio Processing Pipeline Updates**
   - Speech segments uploaded to R2 after generation
   - Background music and sound effects stored in R2
   - Final audio combination streams from R2 sources
   - Temporary file cleanup procedures

3. **Audio File Management**
   - Automated cleanup of old audio files
   - File expiration policies (30 days for demo)
   - Storage usage monitoring and alerts
   - Backup and recovery procedures

4. **Service Layer Updates**
   - Update all audio services to use cloud storage
   - Error handling for upload/download failures
   - Retry logic for transient storage issues
   - Progress tracking for large file operations

### Technical Requirements
- boto3 or similar S3-compatible client
- Async file upload/download methods
- File lifecycle management system
- Storage monitoring and cleanup jobs

### Success Criteria
- [ ] All audio files stored in R2, not database
- [ ] Audio processing pipeline works end-to-end
- [ ] File cleanup procedures working
- [ ] Storage costs under control (< $5/month)

---

## Phase 4: API Enhancements & Demo Integration
**Duration**: 1-2 weeks  
**Dependencies**: Phase 3 complete

### Objectives
- Create simplified demo-specific API endpoints
- Implement text generation service for demo
- Add real-time progress tracking for web UI
- Optimize API responses for web consumption

### Deliverables
1. **Demo API Endpoints**
   - `POST /api/demo/submit` - Single endpoint for demo processing
   - `GET /api/demo/status/{job_id}` - Job status with progress
   - `GET /api/demo/result/{job_id}` - Final audio URL
   - `POST /api/demo/generate-text` - AI text generation

2. **Text Generation Service**
   - Claude-based story generation
   - Multiple prompt templates (adventure, mystery, etc.)
   - Content filtering and safety checks
   - Integration with existing text analysis pipeline

3. **Progress Tracking System**
   - Real-time job status updates
   - Progress percentage calculations
   - Step-by-step progress descriptions
   - Error reporting and user feedback

4. **API Security & Rate Limiting**
   - Basic API key system for demo access
   - Rate limiting (10 requests/minute per IP)
   - Request size limits (50KB text input)
   - Input sanitization and validation

### Technical Requirements
- New API endpoints and routing
- Anthropic Claude integration for text generation
- Job progress calculation logic
- Rate limiting middleware

### Success Criteria
- [ ] Demo workflow works end-to-end from web UI
- [ ] Text generation produces quality content
- [ ] Progress tracking provides clear user feedback
- [ ] API security prevents abuse

---

## Phase 5: Environment Management & CI/CD
**Duration**: 1 week  
**Dependencies**: Phase 4 complete

### Objectives
- Establish proper staging/production environments
- Implement automated deployment pipeline
- Set up monitoring and alerting
- Create rollback procedures

### Deliverables
1. **Environment Separation**
   - Staging environment with separate database/storage
   - Production environment with proper security
   - Environment-specific configuration management
   - Data isolation between environments

2. **CI/CD Pipeline**
   - GitHub Actions workflow for automated testing
   - Automated deployment to staging on feature branches
   - Manual promotion to production after approval
   - Database migration automation

3. **Monitoring & Alerting**
   - Application performance monitoring
   - Error tracking and notification
   - Database performance monitoring
   - Storage usage and cost alerts

4. **Deployment Procedures**
   - Blue-green deployment strategy
   - Rollback procedures for failed deployments
   - Database backup before deployments
   - Health check verification post-deployment

### Technical Requirements
- GitHub Actions workflows
- Environment variable management
- Monitoring service integration
- Backup and restore procedures

### Success Criteria
- [ ] Staging environment mirrors production
- [ ] Automated deployments working reliably
- [ ] Monitoring catches issues before users
- [ ] Rollback procedures tested and documented

---

## Phase 6: Testing, Optimization & Launch Preparation
**Duration**: 1 week  
**Dependencies**: Phase 5 complete

### Objectives
- Perform comprehensive testing of all systems
- Optimize performance for production load
- Prepare for demo launch and user feedback
- Create documentation and runbooks

### Deliverables
1. **Performance Testing**
   - Load testing with simulated demo users
   - Audio processing pipeline performance optimization
   - Database query optimization
   - Storage access pattern optimization

2. **End-to-End Testing**
   - Complete demo workflow testing
   - Error scenario testing and recovery
   - Cross-browser compatibility testing
   - Mobile device testing

3. **Documentation**
   - API documentation (OpenAPI/Swagger)
   - Deployment runbooks
   - Troubleshooting guides
   - User feedback collection procedures

4. **Launch Preparation**
   - Demo content preparation and testing
   - User feedback collection system
   - Analytics and usage tracking
   - Marketing and communication materials

### Technical Requirements
- Load testing tools and scripts
- Performance monitoring dashboards
- Documentation generation tools
- Analytics integration

### Success Criteria
- [ ] System handles expected demo load (50+ concurrent users)
- [ ] All error scenarios handled gracefully
- [ ] Documentation complete and accurate
- [ ] Ready for public demo launch

---

## Risk Assessment & Mitigation

### Technical Risks
1. **Audio Processing Timeouts**
   - Risk: Long processing times cause user abandonment
   - Mitigation: Progress tracking, timeout warnings, optimization

2. **Storage Costs Escalation**
   - Risk: Audio files consume unexpected storage
   - Mitigation: Aggressive cleanup policies, usage monitoring

3. **Database Performance**
   - Risk: Slow queries impact user experience
   - Mitigation: Proper indexing, connection pooling, query optimization

### Business Risks
1. **Service Outages**
   - Risk: Third-party API failures break demo
   - Mitigation: Error handling, fallback options, status page

2. **Cost Overruns**
   - Risk: Cloud costs exceed budget
   - Mitigation: Cost monitoring, usage limits, optimization

---

## Success Metrics

### Technical Metrics
- API response time < 200ms for status checks
- Audio processing completion rate > 95%
- System uptime > 99.5%
- Storage costs < $10/month

### User Experience Metrics
- Demo completion rate > 80%
- Average processing time < 3 minutes
- User satisfaction score > 4/5
- Error rate < 5%

---

## Next Steps

1. **Review and approve this project outline**
2. **Break down Phase 1 into specific tasks**
3. **Set up project management tracking**
4. **Begin Phase 1 implementation**

This document will be updated as the project progresses and requirements evolve.