# Narratix 2.0

Transform written narratives into immersive audio experiences using AI-powered text analysis and voice generation.

## Overview

Narratix analyzes narrative text to identify characters and dialogue, then creates custom AI voices for each character to produce a dramatized audio version of the text. Perfect for publishers, content creators, and audiobook production.

## Key Features

- **Smart Character Detection**: Automatically identifies characters and dialogue in text
- **Custom Voice Generation**: Creates unique voices for each character based on their description
- **High-Quality Audio**: Produces professional-grade audio with proper pacing and expression
- **Efficient Workflow**: Simple command-line interface for end-to-end processing
- **Caching & Optimization**: Intelligent caching for improved performance and reduced API costs

## Requirements

- Python 3.13+
- Anthropic API key (for text analysis)
- Hume API key (for voice generation)
- Optional: ElevenLabs API key (alternative voice provider)

## Installation

```bash
# Clone the repository
git clone https://github.com/andayagi/narratix2.0.git
cd narratix2.0

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

## Configuration

1. Copy the template environment file:
   ```bash
   cp .env.template .env
   ```

2. Edit `.env` with your API keys and configuration:
   ```
   ANTHROPIC_API_KEY=your_key_here
   HUME_API_KEY=your_key_here
   ```

## Quick Start

```bash
# Analyze text and identify characters
narratix analyze --file your_story.txt

# Create voices for characters
narratix voices create "Character Name" "Character description"

# Process a complete narrative
narratix narrative --file your_story.txt --output story_audio
```

## Advanced Usage

See our [Documentation](docs/README.md) for detailed usage instructions, API reference, and examples.

## Development

To set up a development environment:

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black narratix tests
isort narratix tests
```

## Roadmap

See [TASKS.md](TASKS.md) for the development roadmap and upcoming features.

## License

MIT License - See [LICENSE](LICENSE) for details. 