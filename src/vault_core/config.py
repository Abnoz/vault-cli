"""Shared configuration helpers for the Python Vault stack."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence


class ConfigError(RuntimeError):
    """Raised when required configuration values are missing or invalid."""


EnvMapping = Mapping[str, str]


def _get_env(env: Optional[EnvMapping]) -> EnvMapping:
    return env or os.environ


def _default_vault_addr(env: EnvMapping) -> str:
    env_addr = env.get("VAULT_ADDR")
    if env_addr:
        return env_addr

    if env.get("DOCKER"):
        return "http://vault:8200"

    return "http://localhost:8200"


def _default_vault_path(env: EnvMapping) -> str:
    return env.get("VAULT_PATH", "secret/data/dev")


@dataclass(slots=True)
class VaultSettings:
    addr: str
    token: str
    path: str


def load_vault_settings(
    *,
    addr_option: Optional[str],
    token_option: Optional[str],
    path_option: Optional[str],
    env: Optional[EnvMapping] = None,
) -> VaultSettings:
    env = _get_env(env)
    addr = addr_option or _default_vault_addr(env)
    path = path_option or _default_vault_path(env)

    token = token_option or env.get("VAULT_TOKEN")
    if not token:
        raise ConfigError("Vault token is required. Set VAULT_TOKEN or pass --token/-t.")

    return VaultSettings(addr=addr, token=token, path=path)


def _parse_cors(origins: Optional[str]) -> list[str]:
    if not origins:
        return ["*"]
    parsed = [value.strip() for value in origins.split(",") if value.strip()]
    return parsed or ["*"]


@dataclass(slots=True)
class APISettings:
    api_key: str
    port: int
    cors_origins: Sequence[str]


def load_api_settings(
    *,
    api_key_option: Optional[str],
    port_option: Optional[int],
    env: Optional[EnvMapping] = None,
) -> APISettings:
    env = _get_env(env)

    api_key = api_key_option or env.get("API_KEY")
    if not api_key:
        raise ConfigError("API key is required. Set API_KEY or pass --api-key.")

    port_value = port_option if port_option is not None else env.get("PORT", "8000")
    try:
        port = int(port_value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - guard clause
        raise ConfigError(f"Invalid port value: {port_value}") from exc

    cors_origins = _parse_cors(env.get("CORS_ORIGINS"))
    return APISettings(api_key=api_key, port=port, cors_origins=cors_origins)


