#!/bin/bash

# Run integration tests with real API calls
# Usage: ./run_integration_tests.sh [test_file]

# Check if HUME_API_KEY is set
if [ -z "$HUME_API_KEY" ]; then
    echo "ERROR: HUME_API_KEY environment variable is not set."
    echo "Please set it before running the integration tests with:"
    echo "export HUME_API_KEY=your_api_key"
    exit 1
fi

# Path to test file
TEST_FILE=${1:-"tests/test_voice_generation_integration.py"}

# Run pytest with verbose output
echo "Running integration test with real API calls: $TEST_FILE"
python -m pytest -xvs "$TEST_FILE" 