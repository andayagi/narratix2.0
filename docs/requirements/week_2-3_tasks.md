# Weeks 2-3: Domain and Infrastructure Layer Implementation

**Goal:** Implement the core data structures (domain entities) and the foundational infrastructure components like database interaction, logging, and error handling.

## Tasks

### 1. Implement Core Domain Entities
   - **Objective:** Translate the domain entity specifications into concrete Python classes.
   - **Actions:**
     - Create Python classes for `TextContent`, `Character`, `Voice`, and `NarrativeElement` in `src/narratix/core/domain/entities/`.
     - Implement attributes, methods (initially placeholder methods if needed), and basic data validation (e.g., type hints, simple value checks) for each entity based on `docs/requirements/domain_entities.md`.
     - Ensure entities represent the core concepts accurately.
     - Add basic docstrings explaining the purpose of each class and its attributes.
   - **Deliverable:** Python files containing the implementation of core domain entities within the `src/narratix/core/domain/entities/` directory.

### 2. Define Interfaces for Domain Services
   - **Objective:** Establish the contracts for how different parts of the application will interact with core functionalities, promoting loose coupling.
   - **Actions:**
     - Define abstract base classes (ABCs) or Protocol classes for key domain services (e.g., `TextAnalysisService`, `VoiceManagementService`, `AudioGenerationService`) in `src/narratix/core/domain/services/`.
     - Specify the methods and their signatures (inputs, outputs) required for each service interface.
     - These interfaces will guide the implementation of concrete service classes later.
   - **Deliverable:** Python files containing the abstract interfaces for core domain services within `src/narratix/core/domain/services/`.

### 3. Implement Data Repositories with SQLAlchemy
   - **Objective:** Set up the persistence layer to store and retrieve domain entities using an Object-Relational Mapper (ORM) with considerations for future cloud migration.
   - **Actions:**
     - **3.1 Database Configuration**
       - Configure SQLAlchemy within the project (e.g., in `src/narratix/infrastructure/database/`).
       - Use environment variables (`DATABASE_URL`) for database connection settings, defaulting to a local SQLite database (`.env` file) for ease of development.
       - Set up database connection management with a session factory pattern.
     - **3.2 Base Models & Entity Models**
       - Define SQLAlchemy models corresponding to the core domain entities (`TextContent`, `Character`, `Voice`, `NarrativeElement`).
       - Use PostgreSQL-compatible column types (e.g., `UUID`, `JSON`, `DateTime`) where appropriate to ensure future cloud compatibility, even though local development uses SQLite.
       - Document the database schema and relationships between entities.
     - **3.3 Repository Interfaces & Implementation**
       - Define repository interfaces in the domain layer.
       - Implement repository classes that fulfill the repository interfaces, providing methods for CRUD operations against the configured database.
     - **3.4 Migration Setup**
       - Configure Alembic for database schema migrations.
       - Create initial database migration scripts using Alembic based on the defined models and apply them to the local SQLite database.
   - **Deliverable:** Implemented SQLAlchemy models, repository implementations, database configuration (including `.env` for local SQLite), and initial migration scripts applied in `src/narratix/infrastructure/database/` and `alembic/`.

### 4. Set Up Logging and Error Handling
   - **Objective:** Establish consistent mechanisms for logging application events and handling errors gracefully.
   - **Actions:**
     - Configure a standard logging library (e.g., Python's built-in `logging`) in `src/narratix/infrastructure/logging.py` or similar.
     - Define different logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL).
     - Implement basic logging setup (e.g., logging to console and/or a file).
     - Define custom exception classes for application-specific errors in `src/narratix/core/errors.py`.
     - Implement basic error handling mechanisms (e.g., try-except blocks in key areas, potentially a global exception handler if applicable later).
   - **Deliverable:** Configured logging setup and defined custom exception classes.

### 5. Set Up Testing Framework and Basic Tests
   - **Objective:** Ensure the foundational components are testable and write initial tests for core entities and repositories.
   - **Actions:**
     - Confirm `pytest` setup is working correctly.
     - Write basic unit tests for the domain entities (e.g., testing initialization, simple methods). Place tests in `tests/unit/core/domain/`.
     - Write initial integration tests for the data repositories (e.g., testing database interactions, potentially using a test database or mocking). Place tests in `tests/integration/infrastructure/database/`.
     - Configure test fixtures if needed (e.g., for setting up database sessions).
   - **Deliverable:** Initial unit and integration tests for domain entities and repositories, runnable via `pytest`.

## Review Checklist for End of Week 3:

- [x] Core domain entity classes (`TextContent`, `Character`, `Voice`, `NarrativeElement`) implemented.
- [x] Abstract interfaces for core domain services defined.
- [x] SQLAlchemy models and basic repositories implemented.
- [x] Database connection and initial migrations configured.
- [x] Logging configured and basic usage implemented.
- [x] Custom application exceptions defined.
- [x] Basic unit tests for domain entities written and passing.
- [x] Basic integration tests for repositories written and passing. 