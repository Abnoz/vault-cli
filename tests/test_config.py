import pytest

from vault_core.config import (
    APISettings,
    ConfigError,
    VaultSettings,
    _default_vault_addr,
    load_api_settings,
    load_vault_settings,
)


def test_default_addr_prefers_env():
    env = {"VAULT_ADDR": "http://custom:8200"}
    assert _default_vault_addr(env) == "http://custom:8200"


def test_default_addr_respects_docker_hint():
    env = {"DOCKER": "1"}
    assert _default_vault_addr(env) == "http://vault:8200"


def test_default_addr_falls_back_to_localhost():
    assert _default_vault_addr({}) == "http://localhost:8200"


def test_load_settings_requires_token():
    with pytest.raises(ConfigError):
        load_vault_settings(addr_option=None, token_option=None, path_option=None, env={})


def test_load_settings_with_options_and_env():
    env = {"VAULT_TOKEN": "token-from-env", "VAULT_PATH": "secret/data/test"}
    settings = load_vault_settings(
        addr_option="http://override:8200",
        token_option=None,
        path_option=None,
        env=env,
    )
    assert isinstance(settings, VaultSettings)
    assert settings.addr == "http://override:8200"
    assert settings.token == "token-from-env"
    assert settings.path == "secret/data/test"


def test_load_api_settings_parses_cors_list():
    env = {
        "API_KEY": "secret",
        "PORT": "8100",
        "CORS_ORIGINS": "https://example.com,https://other.dev",
    }
    settings = load_api_settings(api_key_option=None, port_option=None, env=env)
    assert isinstance(settings, APISettings)
    assert settings.port == 8100
    assert settings.cors_origins == ["https://example.com", "https://other.dev"]

