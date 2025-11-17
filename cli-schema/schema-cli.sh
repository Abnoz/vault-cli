#!/bin/bash

# Helper script to run schema-cli using Docker

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_DIR"

# Function to run the CLI command
run_cli() {
    docker run --rm \
        -v "$PROJECT_DIR:/workspace" \
        -w /workspace \
        vault-store-schema-cli \
        /app/schema-cli "$@"
}

# Build if image doesn't exist
if ! docker images --format '{{.Repository}}' | grep -q "^vault-store-schema-cli$"; then
    echo "Building schema-cli image..."
    docker build -t vault-store-schema-cli ./cli-schema > /dev/null 2>&1
fi

run_cli "$@"

