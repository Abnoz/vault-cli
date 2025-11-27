# Vault CLI - Python Edition

A comprehensive Python-based toolchain for managing HashiCorp Vault secrets with both command-line interface and REST API. This project provides a complete solution for secret management with project-based organization, environment separation, and modern Python best practices.

## Overview

Vault CLI is a full-featured secret management system that provides:

- **Command-Line Interface (CLI)**: Interactive and scriptable CLI for managing secrets
- **REST API**: FastAPI-based HTTP API for programmatic access and integration
- **Project Management**: Organize secrets by projects and environments (dev, staging, production)
- **Type Safety**: Automatic type detection and preservation for secret values
- **Docker Support**: Complete Docker Compose stack for local development and testing

## Features

### Core Capabilities

- ✅ **Secret Management**: List, get, set, edit, and delete secrets with type preservation
- ✅ **Project Organization**: Create and manage projects with multiple environments
- ✅ **Environment Separation**: Isolate secrets by environment (dev, staging, production)
- ✅ **Interactive CLI**: User-friendly prompts and confirmations
- ✅ **REST API**: Full CRUD operations via HTTP endpoints
- ✅ **Rate Limiting**: Built-in rate limiting for API protection
- ✅ **Authentication**: API key-based authentication for the REST API
- ✅ **Error Handling**: Comprehensive error handling with user-friendly messages
- ✅ **Logging**: Structured logging for debugging and monitoring

### Architecture

The project follows a clean architecture pattern with three main modules:

- **`vault_core`**: Core business logic, Vault client, configuration, and project management
- **`vault_cli`**: Typer-based command-line interface
- **`vault_api`**: FastAPI-based REST API with rate limiting and authentication

## Installation

### Requirements

- Python 3.10 or higher
- HashiCorp Vault instance (local or remote)
- Vault token with appropriate permissions

### Setup

1. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install the package:**
   ```bash
   pip install -e .
   ```

   Or install with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Configure environment variables:**
   ```bash
   export VAULT_ADDR=http://localhost:8200
   export VAULT_TOKEN=your-vault-token
   export API_KEY=your-api-key  # For REST API
   ```

## Usage

### Command-Line Interface

#### Basic Secret Operations

```bash
# List all secrets in the configured path
vault-cli list

# Get a specific secret
vault-cli get POSTGRES_PASSWORD

# Set a secret (automatically detects type)
vault-cli set API_KEY "my-secret-key"
vault-cli set MAX_CONNECTIONS 100
vault-cli set ENABLE_FEATURE true

# Edit a secret interactively
vault-cli edit API_KEY

# Delete a secret (with confirmation)
vault-cli delete OLD_SECRET

# Force delete without confirmation
vault-cli delete OLD_SECRET --force
```

#### Project Management

```bash
# Create a new project with default environments (dev, staging, production)
vault-cli create-project my-project

# Create a project with custom environments
vault-cli create-project my-project --environments dev,test,prod

# List all projects
vault-cli list-projects

# Get project information
vault-cli get-project my-project

# Update project (add/remove environments)
vault-cli update-project my-project --add-environments qa --remove-environments test

# Delete a project and all its environments
vault-cli delete-project my-project
```

#### CLI Options

```bash
# Specify Vault address
vault-cli --addr https://vault.example.com:8200 list

# Use a specific token
vault-cli --token s.xxxxx list

# Configure secrets path
vault-cli --path secret/data/myapp list
```

### REST API

The REST API provides programmatic access to project management operations.

#### Starting the API Server

```bash
# Using uvicorn directly
uvicorn vault_api.app:app --host 0.0.0.0 --port 8000

# Or using the installed command
vault-api  # If configured as a script
```

#### API Endpoints

**Health Check:**
```bash
GET /health
```

**Project Operations:**
```bash
# List all projects
GET /api/v1/projects
Headers: X-API-Key: your-api-key

# Get project details
GET /api/v1/projects/{project_name}
Headers: X-API-Key: your-api-key

# Create a new project
POST /api/v1/projects/{project_name}
Headers: X-API-Key: your-api-key
Body: {"environments": ["dev", "staging", "production"]}  # Optional

# Update a project (add/remove environments)
PUT /api/v1/projects/{project_name}
Headers: X-API-Key: your-api-key
Body: {
  "add_environments": ["qa"],
  "remove_environments": ["test"]
}

# Delete a project
DELETE /api/v1/projects/{project_name}
Headers: X-API-Key: your-api-key
```

#### API Features

- **Rate Limiting**: 100 requests/minute for read operations, 10 requests/minute for write operations
- **Authentication**: API key required via `X-API-Key` header
- **CORS Support**: Configurable CORS origins
- **Error Handling**: Consistent error responses with appropriate HTTP status codes
- **Request Logging**: Automatic logging of all API requests

## Docker Usage

### Quick Start

1. **Create a `.env` file:**
   ```bash
   VAULT_ADDR=http://vault:8200
   VAULT_TOKEN=hvs.xxxxx
   VAULT_UNSEAL_KEY=your-unseal-key
   API_KEY=your-api-key
   DOCKER=1
   ```

2. **Start the Vault stack:**
   ```bash
   docker-compose up -d vault
   docker-compose up vault-init vault-populate
   ```

3. **Use the CLI container:**
   ```bash
   # Start CLI container
   docker-compose --profile cli up -d vault-cli
   
   # Run commands
   docker-compose --profile cli exec vault-cli vault-cli list
   docker-compose --profile cli exec vault-cli vault-cli get POSTGRES_PASSWORD
   ```

4. **Start the API server:**
   ```bash
   docker-compose up -d vault-api
   ```

## Development

### Project Structure

```
vault-cli/
├── src/
│   ├── vault_core/          # Core business logic
│   │   ├── config.py        # Configuration management
│   │   ├── vault.py         # Vault client wrapper
│   │   ├── projects.py      # Project management logic
│   │   ├── sanitization.py  # Input sanitization
│   │   └── schema.py        # Schema validation
│   ├── vault_cli/           # CLI implementation
│   │   ├── cli.py           # Typer commands
│   │   ├── formatting.py    # Output formatting
│   │   ├── io.py            # Interactive I/O
│   │   └── types.py         # Type coercion
│   └── vault_api/           # REST API
│       ├── app.py           # FastAPI application
│       ├── models.py        # Pydantic models
│       ├── dependencies.py  # FastAPI dependencies
│       ├── errors.py        # Error handling
│       ├── helpers.py       # Helper functions
│       ├── decorators.py    # Rate limiting decorators
│       └── rate_limit.py    # Rate limiting configuration
├── tests/                   # Test suite
│   ├── integration/         # Integration tests
│   └── test_*.py           # Unit tests
├── scripts/                # Utility scripts
└── docker-compose.yml      # Docker configuration
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_cli.py

# Run integration tests
pytest tests/integration/
```

### Code Quality

The project uses:
- **Ruff**: Fast Python linter and formatter
- **Pytest**: Testing framework
- **Type Hints**: Full type annotations for better code quality

```bash
# Lint code
ruff check src/

# Format code
ruff format src/
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VAULT_ADDR` | Vault server address | `http://localhost:8200` |
| `VAULT_TOKEN` | Vault authentication token | Required |
| `VAULT_PATH` | Base path for secrets (KV v2) | `secret/data` |
| `API_KEY` | API key for REST API authentication | Required for API |
| `API_PORT` | Port for REST API server | `8000` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `*` |

### CLI Configuration

Configuration can be provided via:
1. Environment variables
2. Command-line flags (`--addr`, `--token`, `--path`)
3. Configuration files (future enhancement)

## Project Management

### Project Structure

Projects organize secrets by application/service:

```
secret/data/
├── my-project/
│   ├── dev/          # Development environment secrets
│   ├── staging/      # Staging environment secrets
│   └── production/   # Production environment secrets
└── another-project/
    ├── dev/
    └── production/
```

### Environment Workflow

1. **Create Project**: Sets up the project structure with default or custom environments
2. **Manage Secrets**: Store secrets per environment
3. **Update Environments**: Add or remove environments as needed
4. **Delete Project**: Remove project and all associated secrets

## Security Considerations

- **API Key Authentication**: REST API requires valid API key
- **Rate Limiting**: Prevents abuse and DoS attacks
- **Input Sanitization**: All inputs are validated and sanitized
- **Error Messages**: Sensitive information is not exposed in error messages
- **Timing-Safe Comparison**: API key verification uses constant-time comparison

## Status

✅ **Production Ready**: All tests passing, full feature parity, Docker setup complete.

### Current Version: 0.1.0

- ✅ CLI with full secret management
- ✅ REST API with project management
- ✅ Project and environment organization
- ✅ Docker Compose stack
- ✅ Comprehensive test suite
- ✅ Clean code architecture
- ✅ Rate limiting and authentication
- ✅ Error handling and logging

## License

MIT License

## Contributing

Contributions are welcome! Please ensure:
- All tests pass
- Code follows the existing style (Ruff)
- Type hints are included
- Documentation is updated

## Support

For issues, questions, or contributions, please open an issue on the project repository.
