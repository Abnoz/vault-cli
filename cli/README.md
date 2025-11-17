# Vault CLI Tool

A command-line interface tool to manage secrets in HashiCorp Vault.

## Installation

### Build from source

```bash
cd cli
go build -o vault-cli main.go
```

Or install globally:

```bash
go install
```

## Usage

### Configuration

Set environment variables or use flags:

```bash
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="your-vault-token"
```

Or use flags:

```bash
vault-cli --addr http://localhost:8200 --token your-token [command]
```

### Commands

#### List all secrets

```bash
vault-cli list
```

#### Get a specific secret

```bash
vault-cli get POSTGRES_PASSWORD
```

#### Add a new secret

```bash
vault-cli add NEW_KEY "new value"
```

#### Edit an existing secret

```bash
vault-cli edit POSTGRES_PASSWORD
```

This will prompt you to enter the new value interactively.

#### Set a secret (add or update)

```bash
vault-cli set POSTGRES_PASSWORD "new password"
```

This will create the secret if it doesn't exist, or update it if it does.

#### Delete a secret

```bash
vault-cli delete OLD_KEY
```

This will prompt for confirmation before deleting.

### Options

- `--addr`: Vault server address (default: http://localhost:8200)
- `--token`: Vault token (or set VAULT_TOKEN env var)
- `--path`: Secret path in Vault (default: secret/data/dev)

### Examples

```bash
# List all secrets
vault-cli list

# Get a specific secret value
vault-cli get AZURE_CLIENT_ID

# Add a new secret
vault-cli add NEW_API_KEY "secret-key-123"

# Update an existing secret
vault-cli set POSTGRES_PASSWORD "newpassword123"

# Edit a secret interactively
vault-cli edit DEBUG

# Delete a secret
vault-cli delete OLD_KEY

# Use custom Vault address and path
vault-cli --addr http://vault:8200 --path secret/data/prod list
```

## Building for Docker

The CLI can be built as a Docker image or used in a container:

```bash
docker build -t vault-cli ./cli
docker run --rm -e VAULT_ADDR=http://vault:8200 -e VAULT_TOKEN=your-token vault-cli list
```

