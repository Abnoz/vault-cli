#!/bin/bash

# Helper script to run vault-cli using Docker
# Reuses existing container if available, otherwise creates a new one

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_DIR"

# Function to run the CLI command
run_cli() {
    # Use regular exec - edit command now accepts value as argument
    docker exec vault-cli ./vault-cli "$@"
}

# Check if vault-cli container exists and is running
if docker ps --format '{{.Names}}' | grep -q "^vault-cli$"; then
    # Container exists and is running, use exec
    run_cli "$@"
elif docker ps -a --format '{{.Names}}' | grep -q "^vault-cli$"; then
    # Container exists but is stopped, start it and use exec
    docker start vault-cli > /dev/null 2>&1
    sleep 1
    run_cli "$@"
else
    # Container doesn't exist, create it and keep it running
    docker-compose --profile cli up -d vault-cli > /dev/null 2>&1
    # Wait a moment for container to be ready
    sleep 1
    run_cli "$@"
fi

