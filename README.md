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

- `narratix/`: Main package
  - `core/`: Core functionality
    - `text_analysis.py`: Text analysis logic
    - `voice_generation.py`: Voice generation
    - `audio_generation.py`: Audio generation
    - `database.py`: Database models
  - `utils/`: Utility functions
    - `config.py`: Configuration settings
    - `logging_config.py`: Logging setup
    - `metrics.py`: Performance metrics
  - `tools/`: CLI tools
    - `view_logs.py`: Log viewing utility
    - `resource_monitor.py`: Resource monitoring
    - `hume_dashboard.py`: Hume AI dashboard
  - `main.py`: Application entry point
- `tests/`: Test suite
- `docs/`: Documentation
- `scripts/`: Helper scripts
- `.github/`: GitHub workflows 