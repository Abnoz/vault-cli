#!/bin/sh
set -e

echo "Initializing Vault..."

# Check if Vault is already initialized
if vault status | grep -q "Initialized.*true"; then
  echo "Vault is already initialized."
  exit 0
fi

# Initialize Vault
if [ -z "$VAULT_UNSEAL_KEY" ]; then
  echo "Initializing Vault (this will generate unseal keys)..."
  INIT_OUTPUT=$(vault operator init -format=json)
  echo "$INIT_OUTPUT" | jq -r '.unseal_keys_b64[0]' > /tmp/unseal_key.txt || true
  echo "$INIT_OUTPUT" | jq -r '.root_token' > /tmp/root_token.txt || true
  echo "Vault initialized. Check logs for unseal keys and root token."
else
  echo "Using provided unseal key..."
  vault operator unseal "$VAULT_UNSEAL_KEY" || true
fi

echo "Vault initialization complete."

