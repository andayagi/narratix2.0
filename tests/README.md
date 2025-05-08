# Narratix Testing

This directory contains tests for the Narratix application.

## Integration Tests

Integration tests use real API calls and database connections. They require the following:

1. API Keys in environment variables:
   - `HUME_API_KEY` - For voice generation testing
   - `ANTHROPIC_API_KEY` - For text analysis testing

2. A database connection (default uses SQLite)

## Running Tests

### Run all tests
```bash
pytest
```

### Run integration tests only
```bash
pytest -m integration
```

### Run voice generation integration test
```bash
# With real API calls (requires HUME_API_KEY)
./tests/run_integration_tests.sh

# Or manually
export HUME_API_KEY=your_actual_api_key
pytest -xvs tests/test_voice_generation_integration.py
```

### Run with specific database
```bash
DATABASE_URL=sqlite:///./test.db pytest
```

## Test Data

The integration tests create real entries in the database and make real API calls. The data is preserved for inspection after the tests run.

## Notes on Voice Generation Test

The `test_voice_generation_integration.py` test:

1. Creates a text record in the database
2. Creates a character linked to that text
3. Makes real API calls to Hume AI to generate a voice
4. Verifies the voice generation worked and updated the database

This is a true integration test with no mocks. It requires a valid Hume API key. 