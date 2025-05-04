# Narratix

A powerful narrative analysis and voice synthesis tool.

## Setup

1. Clone the repository
2. Copy `.env.template` to `.env` and fill in your API keys
3. Install dependencies:
```bash
pip install -e .
```

## Development

- `make test`: Run tests
- `make lint`: Run linters
- `make migrate`: Run database migrations

## Project Structure

- `api/`: REST API interface
- `cli/`: Command-line interface
- `core/`: Core business logic
- `infrastructure/`: External dependencies
- `utils/`: Utility functions
- `tests/`: Test suite 