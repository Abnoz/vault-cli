"""Pytest fixtures for integration tests."""

from __future__ import annotations

import os
import pytest

from vault_core.config import VaultSettings, load_vault_settings
from vault_core.vault import VaultClient


@pytest.fixture(scope="session")
def vault_settings() -> VaultSettings:
    """Get Vault settings from environment."""
    if not os.getenv("VAULT_TOKEN") or not os.getenv("VAULT_ADDR"):
        pytest.skip("Vault not configured (set VAULT_ADDR and VAULT_TOKEN)")

    return load_vault_settings(
        addr_option=os.getenv("VAULT_ADDR"),
        token_option=os.getenv("VAULT_TOKEN"),
        path_option=None,
    )


@pytest.fixture(scope="session")
def vault_client(vault_settings: VaultSettings) -> VaultClient:
    """Create a Vault client for integration tests."""
    return VaultClient(addr=vault_settings.addr, token=vault_settings.token)

