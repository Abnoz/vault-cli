#!/bin/sh
set -e

echo "Populating Vault with test secrets..."

# Wait for Vault to be ready
until vault status >/dev/null 2>&1; do
  echo "Waiting for Vault to be ready..."
  sleep 2
done

# Enable KV v2 secrets engine if not already enabled
if ! vault secrets list | grep -q "secret/"; then
  echo "Enabling KV v2 secrets engine..."
  vault secrets enable -version=2 -path=secret kv || true
fi

# Populate some test secrets
echo "Adding test secrets to secret/data/dev..."
vault kv put secret/data/dev \
  POSTGRES_PASSWORD="test_password_123" \
  API_KEY="test_api_key_456" \
  DEBUG="false" || true

echo "Vault population complete."

