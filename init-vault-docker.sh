#!/bin/bash

# Script to initialize and unseal Vault in production mode using Docker
# This script checks if Vault is initialized, and if not, initializes it
# Then it unseals Vault using the unseal keys

VAULT_ADDR="${VAULT_ADDR:-http://vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"

echo "Waiting for Vault to be ready..."
# Vault returns exit code 2 when not initialized, which is still a valid response
# Exit code 0 = initialized, exit code 2 = not initialized but running
while true; do
  vault status > /dev/null 2>&1
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 2 ]; then
    break
  fi
  echo "Waiting for Vault to start..."
  sleep 2
done

echo "Checking if Vault is initialized..."
VAULT_STATUS=$(vault status -format=json 2>/dev/null)
IS_INITIALIZED=$(echo $VAULT_STATUS | jq -r '.initialized // false')

if [ "$IS_INITIALIZED" != "true" ]; then
  echo "Vault is not initialized. Initializing..."
  
  # Initialize Vault with 1 key share and 1 threshold (for simplicity)
  # In production, you should use more key shares and threshold (e.g., 5 shares, 3 threshold)
  INIT_OUTPUT=$(vault operator init -key-shares=1 -key-threshold=1 -format=json)
  
  if [ $? -eq 0 ]; then
    UNSEAL_KEY=$(echo $INIT_OUTPUT | jq -r '.unseal_keys_b64[0]')
    ROOT_TOKEN=$(echo $INIT_OUTPUT | jq -r '.root_token')
    
    echo "Vault initialized successfully!"
    echo "Unseal key: $UNSEAL_KEY"
    echo "Root token: $ROOT_TOKEN"
    echo ""
    echo "⚠️  IMPORTANT: Save these credentials securely!"
    echo ""
    
    # Unseal Vault
    echo "Unsealing Vault..."
    vault operator unseal $UNSEAL_KEY
    
    # Export root token for subsequent operations
    export VAULT_TOKEN=$ROOT_TOKEN
    
    # Save credentials to file (for reference, but keep secure!)
    echo "UNSEAL_KEY=$UNSEAL_KEY" > /tmp/vault-credentials.txt
    echo "ROOT_TOKEN=$ROOT_TOKEN" >> /tmp/vault-credentials.txt
    echo "Credentials saved to /tmp/vault-credentials.txt (inside container)"
  else
    echo "Failed to initialize Vault"
    exit 1
  fi
else
  echo "Vault is already initialized"
  
  # Check if Vault is sealed
  IS_SEALED=$(echo $VAULT_STATUS | jq -r '.sealed // true')
  
  if [ "$IS_SEALED" = "true" ]; then
    echo "Vault is sealed. Attempting to unseal..."
    
    # Try to unseal using VAULT_UNSEAL_KEY if provided
    if [ -n "$VAULT_UNSEAL_KEY" ]; then
      vault operator unseal $VAULT_UNSEAL_KEY
      if [ $? -eq 0 ]; then
        echo "Vault unsealed successfully"
      else
        echo "Failed to unseal Vault"
        exit 1
      fi
    else
      echo "⚠️  Vault is sealed but VAULT_UNSEAL_KEY is not set."
      echo "You need to manually unseal Vault using:"
      echo "  docker-compose exec vault vault operator unseal <unseal-key>"
      echo ""
      echo "Or set VAULT_UNSEAL_KEY in your .env file and restart."
      # Don't exit with error - allow manual unsealing
      exit 0
    fi
  else
    echo "Vault is unsealed and ready"
  fi
fi

# Verify Vault is ready
if vault status | grep -q "Sealed.*false"; then
  echo "✅ Vault is ready and unsealed!"
else
  echo "❌ Vault is still sealed or not ready"
  exit 1
fi

