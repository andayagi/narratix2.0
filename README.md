# Narratix (Version 2.0)

A tool to convert text narratives into engaging audio experiences using multiple character voices powered by AI Text-to-Speech (TTS).

## Overview

Narratix aims to simplify the creation of audiobooks, podcasts, or dialogue-heavy audio content by automatically identifying characters, assigning distinct voices, and generating high-quality audio output.

This is a rebuild effort focusing on a more robust and extensible architecture compared to the original version.

## Features (Planned)

*   Automatic character detection from script formats.
*   Voice assignment and management.
*   Support for various TTS providers (initially focusing on [Specify Provider, e.g., ElevenLabs, Coqui]).
*   Command-line interface for processing.
*   Extensible architecture for adding new features and TTS engines.

## Getting Started

### Prerequisites

*   Python 3.10+ ([Link to Python installation](https://www.python.org/downloads/))
*   Poetry ([Link to Poetry installation](https://python-poetry.org/docs/#installation))

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [Your Repository URL]
    cd Narratix2.0
    ```

2.  **Install dependencies:**
    ```bash
    poetry install
    ```
    *This command creates a virtual environment (if one doesn't exist) and installs all project dependencies listed in `pyproject.toml`.*

3.  **Configure Environment Variables:**
    *   Create a file named `.env` in the project root directory (the same directory as `pyproject.toml`).
    *   **Database:** For local development, add the following line to configure the SQLite database. The database file (`narratix_local.db`) will be automatically created in the project root when the application first runs migrations or accesses the DB.
        ```dotenv
        # .env
        DATABASE_URL="sqlite:///./narratix_local.db"
        ```
    *   **API Keys:** Add necessary API keys for external services (e.g., TTS provider, text analysis provider). Refer to specific service documentation for required keys.
        ```dotenv
        # .env
        # Example (replace with actual keys and variable names as needed):
        # ANTHROPIC_API_KEY="your_anthropic_key"
        # HUME_API_KEY="your_hume_key"
        ```

4.  **Database Migrations:** Apply the initial database schema:
    ```bash
    poetry run alembic upgrade head
    ```
    *Run this command again after any future changes to the database models.*

5.  **Activate the virtual environment:**
    ```bash
    poetry shell
    ```

6.  **Run Linters/Formatters (Optional but Recommended):**
    ```bash
    # Format code with Black
    poetry run black .
    # Check linting with Ruff (or Flake8/Pylint if configured)
    poetry run ruff check .
    # Or fix automatically
    poetry run ruff check . --fix
    ```

7.  **Run Tests (Optional but Recommended):**
    ```bash
    poetry run pytest
    ```

### Basic Usage (Example - To be refined)

```bash
poetry run narratix process --input ./path/to/your/script.txt --output ./output/audio.mp3
```

## Architecture

For details on the system design, component interactions, and key architectural decisions, please refer to the documents in the `docs/architecture/` directory:

*   [Component Diagram](./docs/architecture/component_diagram.md)
*   [Sequence Diagram Example](./docs/architecture/sequence_diagram_example.md)
*   [Architecture Decision Records (ADRs)](./docs/architecture/decisions.md)

## Contributing

Contribution guidelines will be added soon. Please adhere to the code style enforced by Black and Ruff.

## License

[Specify License - e.g., MIT, Apache 2.0, Proprietary]

## Acknowledgements

- [Anthropic Claude](https://www.anthropic.com/) - Text analysis
- [Hume AI](https://hume.ai/) - Voice generation
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM 