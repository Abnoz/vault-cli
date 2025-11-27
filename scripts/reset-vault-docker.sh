#!/bin/sh
set -e

echo "=========================================="
echo "WARNING: This will DELETE all Vault data!"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Stop the Vault container"
echo "  2. Delete the vault-data directory"
echo "  3. Restart Vault"
echo "  4. Reinitialize Vault with a single unseal key"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

echo ""
echo "Stopping Vault container..."
docker-compose stop vault || true

echo "Removing vault-data directory..."
rm -rf vault-data/*

echo "Starting Vault..."
docker-compose up -d vault

echo "Waiting for Vault to be ready..."
sleep 5

echo "Initializing Vault..."
docker-compose up vault-init

echo ""
echo "=========================================="
echo "Vault reset complete!"
echo "=========================================="
echo ""
echo "Check the vault-init container logs for your unseal key and root token:"
echo "  docker-compose logs vault-init"
echo ""
echo "Then add them to your .env file:"
echo "  VAULT_UNSEAL_KEY=<unseal-key-from-logs>"
echo "  VAULT_TOKEN=<root-token-from-logs>"
echo ""

