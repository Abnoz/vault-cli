#!/bin/bash

# Script to initialize and unseal Vault in production mode
# This script checks if Vault is initialized, and if not, initializes it
# Then it unseals Vault using the unseal keys

VAULT_ADDR="${VAULT_ADDR:-http://vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"

echo "Waiting for Vault to be ready..."
until vault status > /dev/null 2>&1; do
  echo "Waiting for Vault to start..."
  sleep 2
done

echo "Checking if Vault is initialized..."
if ! vault status | grep -q "Initialized.*true"; then
  echo "Vault is not initialized. Initializing..."
  
  # Initialize Vault with 1 key share and 1 threshold (for simplicity)
  # In production, you should use more key shares and threshold
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
    
    # If VAULT_TOKEN is provided in env, update it with root token
    if [ -n "$VAULT_TOKEN" ]; then
      echo "Note: Using provided VAULT_TOKEN from environment"
      export VAULT_TOKEN=$ROOT_TOKEN
    fi
  else
    echo "Failed to initialize Vault"
    exit 1
  fi
else
  echo "Vault is already initialized"
  
  # Check if Vault is sealed
  if vault status | grep -q "Sealed.*true"; then
    echo "Vault is sealed. Attempting to unseal..."
    
    # Try to unseal using VAULT_UNSEAL_KEY if provided
    if [ -n "$VAULT_UNSEAL_KEY" ]; then
      vault operator unseal $VAULT_UNSEAL_KEY
    else
      echo "⚠️  Vault is sealed but VAULT_UNSEAL_KEY is not set."
      echo "You need to manually unseal Vault using:"
      echo "  vault operator unseal <unseal-key>"
      exit 1
    fi
  else
    echo "Vault is unsealed and ready"
  fi
fi

echo "✅ Vault is ready!"

