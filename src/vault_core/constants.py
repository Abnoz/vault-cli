"""Constants used across the Vault CLI application."""

from __future__ import annotations

# Default Vault paths
DEFAULT_VAULT_BASE_PATH = "secret/data"
DEFAULT_ENVIRONMENTS = ["dev", "staging", "production"]

# Validation limits
MAX_PROJECT_NAME_LENGTH = 100
MAX_ENVIRONMENT_NAME_LENGTH = 50

# Path component validation
ALLOWED_PATH_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")

