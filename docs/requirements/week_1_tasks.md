# Week 1: Project Setup and Core Planning

**Goal:** Establish the foundational structure, tools, and core design concepts for the Narratix rebuild.

## Tasks

### 1. Set Up Project Structure
   - **Objective:** Create a clean, scalable directory layout.
   - **Actions:**
     - Initialize the main project directory.
     - Create top-level directories: `src/narratix`, `tests`, `docs`, `scripts`.
     - Define initial sub-modules within `src/narratix`: `core`, `services`, `infrastructure`, `cli`.
     - Add `__init__.py` files to necessary directories to define them as Python packages.
     - Create placeholder files (e.g., `main.py`, core module files) to establish the structure.
   - **Deliverable:** A well-defined directory structure committed to the repository.

### 2. Define Detailed Specifications for Domain Entities
   - **Objective:** Clearly outline the core data structures of the application.
   - **Actions:**
     - Draft the attributes, methods, and relationships for `TextContent`.
     - Draft the attributes, methods, and relationships for `Character`.
     - Draft the attributes, methods, and relationships for `Voice`.
     - Draft the attributes, methods, and relationships for `NarrativeElement` (or similar concept for story structure).
     - Consider data validation rules for each entity.
   - **Deliverable:** A document (`docs/requirements/domain_entities.md`) detailing the specifications for each core domain entity.

### 3. Create Architectural Diagrams and Initial Documentation
   - **Objective:** Visualize the system's high-level design and start essential documentation.
   - **Actions:**
     - Create a high-level component diagram showing major parts (CLI, Services, Core, Infrastructure) and their interactions.
     - Develop a basic sequence diagram for a key use case (e.g., processing a short text snippet).
     - Start the main project `README.md` including:
       - Project overview.
       - Initial setup instructions.
       - Link to architectural documents.
     - Create an `docs/architecture/decisions.md` file to log significant architectural choices (ADRs).
   - **Deliverable:** Initial `README.md`, component diagram, sequence diagram, and ADR file stored in `docs/architecture/`.

### 4. Set Up Development Environment and Tools
   - **Objective:** Configure the necessary tools for development, testing, and quality control.
   - **Actions:**
     - Initialize `git` repository.
     - Create a comprehensive `.gitignore` file (using a standard Python template).
     - Choose and set up a dependency manager (e.g., Poetry):
       - Initialize `pyproject.toml`.
     - Configure linters (`ruff` preferred for integration, or `flake8`/`pylint`) and formatter (`black`). Add configuration files (e.g., `.flake8`, `pyproject.toml` section for `black`).
     - Set up the testing framework (`pytest`). Create `pytest.ini` or configure in `pyproject.toml`.
     - Create initial `requirements.txt` or lock file (`poetry.lock`).
     - Document the complete environment setup process in the `README.md`.
   - **Deliverable:** A fully configured development environment with linting, formatting, testing, and dependency management ready. Setup instructions documented in `README.md`.

## Review Checklist for End of Week 1:

- [x] Project directory structure created and committed.
- [x] Domain entity specifications drafted and documented.
- [x] Initial architectural diagrams created.
- [x] `README.md` and `docs/architecture/decisions.md` initiated.
- [x] Git repository initialized with `.gitignore`.
- [x] Dependency management is set up.
- [x] Linters and formatters are configured.
- [x] Testing framework is configured.
- [x] Environment setup is documented in `README.md`. 