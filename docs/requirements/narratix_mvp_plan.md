# Narratix MVP Rebuild Action Plan

## Project Overview

**Goal:** Rebuild Narratix with a clean, maintainable architecture focusing on short story processing as the MVP.

**Timeline:** 10 weeks

**Development Approach:** All coding will be done by Cursor AI, with human supervision and direction.

## Project Management Approach

### Solo Development with AI

- **Development Cadence:** Weekly milestones with clear deliverables
- **Planning:** Define detailed task list at project start, refine weekly
- **Check-in Pattern:** Regular reviews of generated code
- **Quality Control:** Human review and testing of all AI-generated code

## MVP Features Scope

1. **Text Analysis**
   - Character and dialogue identification
   - Text segmentation by speaker
   - Emotion/tone annotation

2. **Voice Management**
   - Voice profile creation and storage
   - Basic voice customization
   - Voice reuse across stories

3. **Audio Generation**
   - Text-to-speech with character voices
   - Basic audio segment assembly
   - MP3 output format

4. **Command Line Interface**
   - Process complete short stories
   - Manage voice profiles
   - Preview character voices

## Implementation Phases

### Phase 1: Core Architecture Setup (Weeks 1-3)

#### Week 1: Project Setup and Planning
- [x] Set up project structure with clear module boundaries
- [x] Define detailed specifications for domain entities
- [x] Create architectural diagrams and documentation
- [x] Set up development environment and tools

#### Weeks 2-3: Domain and Infrastructure Layer
- [x] Implement core domain entities (TextContent, Character, Voice, NarrativeElement)
- [x] Define interfaces for domain services
- [x] Implement data repositories with SQLAlchemy
- [x] Set up logging and error handling
- [x] Set up testing framework and basic tests

### Phase 2: Basic Services Implementation (Weeks 4-6)

#### Week 4: Text Analysis Services
- [ ] Implement unified Anthropic service for text analysis
- [ ] Create prompt templates for text segmentation and character identification (Note: Character ID uses a detailed JSON-based prompt/response)
- [ ] Implement response parsing and data structures (Note: Character ID parsing handles detailed JSON and populates extended `Character` entity)
- [ ] Add comprehensive testing and error handling

#### Week 5: Voice Management Services
- [ ] Implement Hume client for voice generation
- [ ] Create voice profile management service
- [ ] Develop voice storage and retrieval system

#### Week 6: Core Service Integration and Testing
- [ ] Integrate text analysis and voice management
- [ ] Write comprehensive tests for all services
- [ ] Document all APIs and service interfaces

### Phase 3: Audio Generation and CLI (Weeks 7-9)

#### Week 7: Audio Services
- [ ] Implement text-to-speech service
- [ ] Create audio segment processing
- [ ] Develop audio assembly service

#### Week 8: Command Line Interface
- [ ] Implement base CLI framework
- [ ] Create commands for text analysis
- [ ] Develop commands for voice management
- [ ] Build commands for audio generation

#### Week 9: End-to-End Integration
- [ ] Connect all components into complete workflows
- [ ] Implement comprehensive error handling
- [ ] Create end-to-end tests for complete story processing

### Phase 4: Documentation and Refinement (Week 10)

#### Week 10: Final Documentation and Quality Assurance
- [ ] Create developer documentation
- [ ] Write user guides for CLI
- [ ] Conduct final QA and regression testing
- [ ] Prepare deployment package

## Risk Management

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| AI code quality issues | High | Medium | Regular code reviews, increment complexity gradually |
| AI API changes | High | Medium | Abstract APIs behind interfaces, monitor for changes |
| Complex character identification | Low | Low | Leverage Claude's capabilities directly |
| Audio quality issues | High | Medium | Implement quality checks, voice profile optimization |
| Claude API reliability | High | Medium | Implement robust error handling and retry logic |

## Definition of Done

- All specified features implemented
- Tests passing with >90% coverage
- Documentation completed and reviewed
- Code reviewed and manually verified
- All known bugs fixed
- Performance meets specifications

## Post-MVP Roadmap

1. E-book processing capabilities
2. Web API for remote access
3. Batch processing for multiple stories
4. Advanced voice customization
5. Audio effects and sound design

This plan provides a structured approach to rebuilding Narratix with Cursor AI as the primary developer, focusing on clean architecture and maintainability, while delivering an MVP that handles short story processing effectively. 
