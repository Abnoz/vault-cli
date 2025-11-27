#!/bin/sh
# Don't use set -e here as we need to handle exit codes manually

echo "Initializing Vault..."

# Wait for Vault to be ready (responding to requests)
# Exit code 0 = initialized, 2 = not initialized but responding, 1 = error/not ready
echo "Waiting for Vault to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  # Use || true to prevent script from exiting on error
  vault status >/dev/null 2>&1 || true
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 2 ]; then
    # Exit code 0 = initialized, 2 = not initialized but responding (both are OK)
    echo "Vault is ready."
    break
  else
    # Exit code 1 or other - Vault is not ready yet
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
      echo "Waiting for Vault to be ready... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
      sleep 2
    else
      echo "ERROR: Vault did not become ready after $MAX_ATTEMPTS attempts."
      echo "Please check that the Vault container is running: docker-compose ps vault"
      echo "Vault logs: docker-compose logs vault"
      exit 1
    fi
  fi
done

# Now enable strict error handling for the rest of the script
set -e

# Check if Vault is initialized
INITIALIZED=$(vault status -format=json 2>/dev/null | jq -r '.initialized' 2>/dev/null || echo "false")
SEALED=$(vault status -format=json 2>/dev/null | jq -r '.sealed' 2>/dev/null || echo "true")

if [ "$INITIALIZED" = "true" ]; then
  echo "Vault is already initialized."

  # Check if Vault is sealed and unseal if needed
  if [ "$SEALED" = "true" ]; then
    echo "Vault is sealed. Attempting to unseal..."
if [ -z "$VAULT_UNSEAL_KEY" ]; then
      echo "ERROR: Vault is sealed but VAULT_UNSEAL_KEY is not set."
      echo "Please set VAULT_UNSEAL_KEY in your .env file with one of the unseal keys."
      exit 1
    else
      echo "Using provided unseal key to unseal Vault..."
      vault operator unseal "$VAULT_UNSEAL_KEY" || {
        echo "ERROR: Failed to unseal Vault. The unseal key may be incorrect or more keys may be required."
        exit 1
      }
      echo "Vault unsealed successfully."
    fi
  else
    echo "Vault is already unsealed."
  fi
else
  echo "Vault is not initialized. Initializing..."
  
  # Initialize Vault with a single unseal key for development (threshold=1, shares=1)
  echo "Initializing Vault with single unseal key (development mode)..."
  INIT_OUTPUT=$(vault operator init -format=json -key-shares=1 -key-threshold=1)
  
  UNSEAL_KEY=$(echo "$INIT_OUTPUT" | jq -r '.unseal_keys_b64[0]')
  ROOT_TOKEN=$(echo "$INIT_OUTPUT" | jq -r '.root_token')
  
  # Save to temporary files (these will be lost when container stops)
  echo "$UNSEAL_KEY" > /tmp/unseal_key.txt || true
  echo "$ROOT_TOKEN" > /tmp/root_token.txt || true
  
  # Also print to stdout so it appears in docker logs
  echo "=========================================="
  echo "Vault initialized successfully!"
  echo "=========================================="
  echo ""
  echo "UNSEAL_KEY=$UNSEAL_KEY"
  echo "ROOT_TOKEN=$ROOT_TOKEN"
  echo ""
  echo "=========================================="
  echo "IMPORTANT: Copy these values to your .env file!"
  echo "=========================================="
  echo ""
  echo "Add these lines to your .env file:"
  echo "  VAULT_UNSEAL_KEY=$UNSEAL_KEY"
  echo "  VAULT_TOKEN=$ROOT_TOKEN"
  echo ""
  
  # Unseal Vault with the generated key
  echo "Unsealing Vault..."
  vault operator unseal "$UNSEAL_KEY" || {
    echo "ERROR: Failed to unseal Vault after initialization."
    exit 1
  }
  echo "Vault unsealed successfully."
fi

echo "Vault initialization complete."

