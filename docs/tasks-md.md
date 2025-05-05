# Narratix 2.0 Development Tasks

This document outlines the planned development tasks for rebuilding Narratix with a cleaner architecture.

## Phase 1: Core Infrastructure

### Initial Setup
- [x] Create basic directory structure
- [x] Configure Python environment (Python 3.13+)
- [x] Set up git repository
- [x] Add basic .gitignore, .gitattributes, and LICENSE
- [x] Create README.md with installation instructions
- [x] Create setup.py and requirements.txt

### Configuration & Utilities
- [x] Implement config.py (environment variables, paths)
- [x] Implement logging_config.py (structured logging)
- [ ] Implement metrics collection for API usage

### Database
- [x] Create SQLite database schema for voice management
- [x] Implement database.py with connection pooling
- [x] Add voice CRUD operations
- [ ] Add text analysis storage

## Phase 2: Core Functionality

### Text Analysis
- [ ] Implement Anthropic API integration
- [ ] Create character identification from narrative text
- [ ] Create text segmentation by character/speaker
- [ ] Add caching for previously analyzed texts
- [ ] Implement efficient batching for longer texts

### Voice Generation
- [ ] Integrate with Hume API (primary)
- [ ] Add voice creation, management, and deletion
- [ ] Implement intelligent voice caching
- [ ] Add rate limiting and retry logic
- [ ] Implement voice database sync

### Audio Generation
- [ ] Create async audio generation pipeline
- [ ] Implement text-to-speech with character voices
- [ ] Add audio caching for performance
- [ ] Create audio segment combination
- [ ] Support multiple output formats

## Phase 3: CLI and Tools

### Main CLI
- [ ] Create main.py entry point
- [ ] Implement text analysis commands
- [ ] Implement voice management commands
- [ ] Implement audio generation commands
- [ ] Create narrative workflow command

### Utilities & Tools
- [ ] Implement view_logs.py for log analysis
- [ ] Create resource_monitor.py for system monitoring
- [ ] Create hume_dashboard.py for API metrics

## Phase 4: Testing & Documentation

### Testing
- [ ] Write unit tests for core modules
- [ ] Create integration tests for API workflows
- [ ] Add test fixtures and mocks
- [ ] Set up CI with GitHub Actions

### Documentation
- [ ] Write comprehensive API documentation
- [ ] Create usage examples
- [ ] Document CLI commands
- [ ] Add architecture overview

## Phase 5: Optimizations & Features

### Optimizations
- [ ] Optimize API usage and batching
- [ ] Implement advanced caching strategies
- [ ] Add concurrent processing where appropriate
- [ ] Optimize audio quality vs. size

### Features
- [ ] Add support for custom voice settings (speed, pitch)
- [ ] Implement chapter splitting for long texts
- [ ] Add background music/effects options
- [ ] Create simple web UI for demo purposes


