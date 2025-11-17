# HashiCorp Vault with Docker

This project sets up HashiCorp Vault using Docker Compose with a FastAPI service to read secrets via REST API.

## Prerequisites

- Docker
- Docker Compose
- Vault CLI (optional, for manual operations)

## Quick Start

1. **Create .env file:**
   ```bash
   # Create .env file with required variables
   cat > .env << EOF
   VAULT_TOKEN=
   VAULT_UNSEAL_KEY=
   API_KEY=RHClvahCzd6gqbO4teZtQgFFarCRRYdEXcZpbguthqw
   EOF
   ```

2. **Start Vault (this will initialize it on first run):**
   ```bash
   docker-compose up -d
   ```

3. **Get Vault credentials from initialization logs:**
   ```bash
   # Check the vault-init container logs for root token and unseal key
   docker-compose logs vault-init
   ```
   
   You'll see output like:
   ```
   Unseal key: <your-unseal-key>
   Root token: <your-root-token>
   ```

4. **Update .env file with credentials:**
   ```bash
   # Edit .env and add the root token and unseal key
   # VAULT_TOKEN=<your-root-token>
   # VAULT_UNSEAL_KEY=<your-unseal-key>
   ```

5. **Restart services to apply credentials:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```
   
   The populate script will run automatically and store all secrets in Vault.

6. **Access Services:**
   - Vault UI: http://localhost:8200
   - Vault API: http://localhost:8001
   - API Docs: http://localhost:8001/docs
   - **API Key Required**: All API endpoints require `X-API-Key` header
   - **Default API Key**: `RHClvahCzd6gqbO4teZtQgFFarCRRYdEXcZpbguthqw` (change in production!)
   - **Vault Token**: See `.env.example` or docker-compose.yml for the secure token

5. **Stop Services:**
   ```bash
   docker-compose down
   ```

## Schema Management CLI

A command-line tool is available to manage the secrets schema YAML file.

### Quick Start

```bash
# List all secret definitions in schema
./cli-schema/schema-cli.sh list

# Get a specific definition
./cli-schema/schema-cli.sh get POSTGRES_SERVER

# Add a new variable definition
./cli-schema/schema-cli.sh add NEW_VAR string true "Description"

# Edit a variable property
./cli-schema/schema-cli.sh edit POSTGRES_PORT type integer

# Delete a variable definition
./cli-schema/schema-cli.sh delete OLD_VAR
```

For more details, see [Schema CLI README](./cli-schema/README.md).

## Vault Secrets Management CLI

A command-line tool is available to manage secrets in Vault (the actual secret values).

### Quick Start

```bash
# Using Docker (recommended)
docker-compose --profile cli run --rm vault-cli list

# Or use the helper script
./cli/vault-cli.sh list
```

### Available Commands

- **List all secrets:**
  ```bash
  docker-compose --profile cli run --rm vault-cli list
  ```

- **Get a specific secret:**
  ```bash
  docker-compose --profile cli run --rm vault-cli get POSTGRES_PASSWORD
  ```

- **Add a new secret:**
  ```bash
  docker-compose --profile cli run --rm vault-cli add NEW_KEY "value"
  ```

- **Edit an existing secret:**
  ```bash
  docker-compose --profile cli run --rm vault-cli edit POSTGRES_PASSWORD
  ```

- **Set a secret (add or update):**
  ```bash
  docker-compose --profile cli run --rm vault-cli set POSTGRES_PASSWORD "newpassword"
  ```

- **Delete a secret:**
  ```bash
  docker-compose --profile cli run --rm vault-cli delete OLD_KEY
  ```

For more details, see [CLI README](./cli/README.md).

## Using Vault CLI (Official)

### Option 1: Use Vault CLI from within the container

```bash
# Execute commands inside the container
docker-compose exec vault vault status
docker-compose exec vault vault auth myroot
docker-compose exec vault vault kv put secret/hello foo=world
docker-compose exec vault vault kv get secret/hello
```

### Option 2: Install Vault CLI locally

1. **Install Vault CLI:**
   - macOS: `brew install vault`
   - Or download from: https://www.vaultproject.io/downloads

2. **Set environment variables:**
   ```bash
   export VAULT_ADDR='http://localhost:8200'
   export VAULT_TOKEN='myroot'
   ```

3. **Use Vault commands:**
   ```bash
   vault status
   vault kv put secret/hello foo=world
   vault kv get secret/hello
   ```

## Configuration

- **Port:** 8200 (change in docker-compose.yml if needed)
- **Storage:** File storage backend (data persisted in `./vault-data`)
- **Data Directory:** `./vault-data` (persisted locally - contains `vault.db` and other files)
- **Config Directory:** `./vault-config` (contains `vault.hcl` configuration file)
- **Mode:** Production mode with file storage (data persists across restarts)

## Important Notes

✅ **This setup uses Vault in PRODUCTION mode with file storage**

- Data is persisted to `./vault-data` directory
- Vault must be initialized and unsealed on first run
- Unseal key and root token are generated during initialization
- Save credentials securely - you'll need them to unseal Vault after restarts

**For production deployment:**
- Configure TLS/SSL (currently disabled for local development)
- Use more unseal key shares (e.g., 5 shares, 3 threshold) for better security
- Set up proper authentication methods
- Use secure root token
- Enable audit logging

## Example Commands

```bash
# Enable KV secrets engine
vault secrets enable -path=secret kv-v2

# Write a secret
vault kv put secret/myapp/config username=admin password=secret123

# Read a secret
vault kv get secret/myapp/config

# List secrets
vault kv list secret/

# Delete a secret
vault kv delete secret/myapp/config
```

## Populating Vault with Secrets

The populate script runs automatically when you start the services with `docker-compose up`. It will:
1. Wait for Vault to be initialized and unsealed
2. Enable the KV v2 secrets engine
3. Store all environment variables in the `secret/dev` path

### Manual Population (if needed)

If you need to manually populate Vault:

```bash
# Using Docker (no Vault CLI needed)
docker-compose exec vault vault kv put secret/dev KEY=value
```

Or run the populate script manually:
```bash
./populate-vault-docker.sh
```

### Option 2: Using Vault CLI locally

1. **Install Vault CLI locally** (if not already installed):
   ```bash
   # macOS
   brew install vault
   
   # Or download from: https://www.vaultproject.io/downloads
   ```

2. **Set environment variables:**
   ```bash
   export VAULT_ADDR='http://localhost:8200'
   export VAULT_TOKEN='myroot'
   ```

3. **Run the populate script:**
   ```bash
   chmod +x populate-vault.sh
   ./populate-vault.sh
   ```

### Option 3: Manual commands using Docker

```bash
# Enable KV v2 secrets engine
docker-compose exec vault vault secrets enable -path=secret kv-v2

# Add secrets manually
docker-compose exec vault vault kv put secret/database POSTGRES_SERVER=postgres POSTGRES_USER=postgres
```

## Using the Secrets API

The FastAPI service provides REST endpoints to read secrets from Vault.

### API Endpoints

- **GET /** - API information and available endpoints
- **GET /health** - Health check
- **GET /api/v1/secrets** - List all available secret paths
- **GET /api/v1/secrets/dev** - Get all secrets from the 'dev' path
- **GET /api/v1/secrets/{path}** - Get all secrets from a specific path
- **GET /api/v1/secrets/{path}/{key}** - Get a specific key from a path

### Example API Calls

**All API endpoints require the `X-API-Key` header in the request:**

```bash
# Default API key (change in production!)
API_KEY="RHClvahCzd6gqbO4teZtQgFFarCRRYdEXcZpbguthqw"

# Get all secrets from dev path
curl -H "X-API-Key: $API_KEY" http://localhost:8001/api/v1/secrets/dev

# Get a specific key from dev path
curl -H "X-API-Key: $API_KEY" http://localhost:8001/api/v1/secrets/dev/POSTGRES_PASSWORD

# List all available paths
curl -H "X-API-Key: $API_KEY" http://localhost:8001/api/v1/secrets

# Health check (no API key required)
curl http://localhost:8001/health
```

**Example with inline API key:**
```bash
curl -H "X-API-Key: RHClvahCzd6gqbO4teZtQgFFarCRRYdEXcZpbguthqw" \
  http://localhost:8001/api/v1/secrets/dev/POSTGRES_PASSWORD
```

**Without API Key (will return 401 Unauthorized):**
```bash
curl http://localhost:8001/api/v1/secrets/dev
# Returns: {"detail":"API key required. Please provide X-API-Key header in your request."}
```

**With Invalid API Key (will return 403 Forbidden):**
```bash
curl -H "X-API-Key: wrong-key" http://localhost:8001/api/v1/secrets/dev
# Returns: {"detail":"Invalid API key"}
```

### API Key Configuration

The API key is configured via the `API_KEY` environment variable. You can:

1. **Set it in docker-compose.yml** (default shown)
2. **Use a .env file** (recommended for production)
3. **Pass it as environment variable** when starting services

**Generate a new API key:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Generate a new Vault token (for dev mode, without hvs. prefix):**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## Secret Paths Structure

Secrets are organized in the following paths:

- `secret/database` - Database configuration (PostgreSQL)
- `secret/redis` - Redis and Celery configuration
- `secret/security` - Security tokens and keys
- `secret/api` - API configuration
- `secret/azure` - Azure services configuration
- `secret/marvick` - Marvick/Llama configuration
- `secret/app` - Application settings
- `secret/dev` - All variables in a single path (development environment)

## Troubleshooting

- **Check logs:**
  ```bash
  docker-compose logs vault
  docker-compose logs vault-api
  ```

- **Restart services:**
  ```bash
  docker-compose restart vault
  docker-compose restart vault-api
  ```

- **Remove all data:** `docker-compose down -v` (⚠️ deletes all secrets and vault-data)

- **Unseal Vault manually (if needed):**
  ```bash
  # If Vault becomes sealed after restart, unseal it:
  docker-compose exec vault vault operator unseal <your-unseal-key>
  ```

- **Check Vault initialization status:**
  ```bash
  docker-compose exec vault vault status
  ```

- **Verify Vault is accessible:**
  ```bash
  docker-compose exec vault vault status
  ```

- **Test API connection:**
  ```bash
  curl http://localhost:8001/health
  ```

- **Port conflict on 8000?** The API now runs on port 8001. If you need to change it, edit `docker-compose.yml` and update the port mapping.

# vault-cli
