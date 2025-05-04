# Narratix 2.0 Development Tasks

This document outlines the planned development tasks for rebuilding Narratix with a cleaner architecture.

## Phase 1: Core Infrastructure

### Initial Setup
- [x] Create basic directory structure
- [ ] Configure Python environment (Python 3.13+)
- [ ] Set up git repository
- [ ] Add basic .gitignore, .gitattributes, and LICENSE
- [ ] Create README.md with installation instructions
- [ ] Create setup.py and requirements.txt

### Configuration & Utilities
- [ ] Implement config.py (environment variables, paths)
- [ ] Implement logging_config.py (structured logging)
- [ ] Implement metrics collection for API usage

### Database
- [ ] Create SQLite database schema for voice management
- [ ] Implement database.py with connection pooling
- [ ] Add voice CRUD operations
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

## Immediate Next Steps

1. Set up the basic environment and project structure
2. Implement core utilities (logging, config)
3. Build the database layer
4. Start implementing the text analysis module
5. Begin voice generation integration

## Lean Development Principles

- Start with a minimal viable product
- Focus on core functionality first
- Test thoroughly before adding features
- Document as you go
- Refactor early and often
