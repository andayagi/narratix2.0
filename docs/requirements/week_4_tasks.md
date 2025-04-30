# Week 4: Text Analysis Services Implementation

**Goal:** Implement the core text analysis components including the Anthropic client integration, text segmentation, and character identification services.

## Tasks

### 1. Implement Anthropic Client for Text Analysis
   - **Objective:** Create a client to interact with Anthropic's API for text analysis capabilities.
   - **Actions:**
     - Create an `AnthropicClient` class in `src/narratix/infrastructure/external/anthropic.py`
     - Implement authentication using environment variables for API key management
     - Develop methods for sending text to Claude and processing responses
     - Add basic error handling for API failures
     - Implement basic request limiting to avoid rate limits
     - Write simple unit tests
   - **Deliverable:** Working Anthropic client.

### 2. Develop Character Identification Service
   - **Objective:** Create a service to identify characters throughout a text, extracting detailed attributes for voice generation.
   - **Actions:**
     - Create interface in `src/narratix/core/domain/interfaces.py` for `CharacterIdentificationService`
     - Implement concrete service in `src/narratix/services/character_identification.py`
     - Design detailed prompt template for character extraction via Claude, specifying JSON output format.
     - Update `Character` data structure (`src/narratix/core/domain/entities/character.py`) to include `is_narrator`, `speaking`, `persona_description`, and `text` attributes.
     - Create parsers to transform Claude's detailed JSON responses into `Character` domain entities.
     - Write unit tests covering various response scenarios, including parsing detailed attributes and error handling.
   - **Deliverable:** Character identification service that extracts characters along with their narrator status, speaking status, persona description, and introductory text from a detailed JSON response.

### 3. Create Text Segmentation Service
   - **Objective:** Develop a service that can separate text into logical segments.
   - **Actions:**
     - Create interface in `src/narratix/core/domain/interfaces.py` for `TextSegmentationService`
     - Implement concrete service in `src/narratix/services/text_segmentation.py`
     - Design simple prompt templates for segmenting text
     - Develop data structures to represent segmented text
     - Implement parsing logic for Claude's segmentation responses
     - Add basic classification for dialogue vs. non-dialogue
     - Write simple unit tests
   - **Deliverable:** Text segmentation service that identifies basic segments.

### 4. Integration and Testing
   - **Objective:** Ensure the text analysis components work together correctly.
   - **Actions:**
     - Create simple integration test in `tests/integration/text_analysis_test.py`
     - Write basic unit tests focusing on happy path scenarios
     - Create minimal test fixtures with simple text examples
     - Verify basic functionality works end-to-end
   - **Deliverable:** Basic test suite for core functionality.

### 5. Documentation
   - **Objective:** Document the text analysis components.
   - **Actions:**
     - Add docstrings to public methods
     - Include prompt templates as comments in the code
     - Update README with basic usage example
   - **Deliverable:** Basic inline documentation.

## Review Checklist for End of Week 4:

- [x] Anthropic client implemented with basic error handling
- [x] Character identification service implemented for extracting detailed character attributes (name, narrator status, speaking status, persona, intro text)
- [ ] Text segmentation service implemented for basic segmentation
- [ ] Integration test confirming components work together
- [ ] Documentation covers basic usage
- [ ] Core MVP functionality working 