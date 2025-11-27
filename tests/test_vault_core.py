from __future__ import annotations

from typing import Any, Dict

import pytest
from hvac import exceptions as hvac_exceptions

from vault_core.vault import VaultClient, VaultClientError, _split_kv2_path


def test_split_kv2_path_with_data_segment():
    mount, path = _split_kv2_path("secret/data/dev")
    assert mount == "secret"
    assert path == "dev"


def test_split_kv2_path_without_data_segment():
    mount, path = _split_kv2_path("secret/dev")
    assert mount == "secret"
    assert path == "dev"


def test_split_kv2_path_invalid():
    with pytest.raises(VaultClientError):
        _split_kv2_path("secret")


class DummyHVACClient:
    def __init__(self) -> None:
        self.read_calls: list[Dict[str, Any]] = []
        self.write_calls: list[Dict[str, Any]] = []
        self._data: Dict[str, Dict[str, Any]] = {}

    class _KV2:
        def __init__(self, outer: "DummyHVACClient") -> None:
            self._outer = outer

        def read_secret_version(self, mount_point: str, path: str):
            key = f"{mount_point}/{path}"
            self._outer.read_calls.append({"mount_point": mount_point, "path": path})
            if key not in self._outer._data:
                raise hvac_exceptions.InvalidPath("Path not found")
            return {"data": {"data": self._outer._data[key]}}

        def create_or_update_secret(self, mount_point: str, path: str, secret: Dict[str, Any]):
            key = f"{mount_point}/{path}"
            self._outer.write_calls.append(
                {"mount_point": mount_point, "path": path, "secret": secret},
            )
            self._outer._data[key] = secret

    class _Secrets:
        def __init__(self, outer: "DummyHVACClient") -> None:
            self.kv = type("KV", (), {"v2": DummyHVACClient._KV2(outer)})()

    @property
    def secrets(self) -> "_Secrets":
        return DummyHVACClient._Secrets(self)


def test_vault_client_read_and_write_with_dummy_client(monkeypatch):
    dummy = DummyHVACClient()

    def fake_client(url: str, token: str, timeout: float):  # noqa: ARG001
        return dummy

    monkeypatch.setattr("vault_core.vault.hvac.Client", fake_client)

    client = VaultClient(addr="http://vault:8200", token="t", max_retries=1)

    # Initially, reading returns empty dict when path doesn't exist (InvalidPath is caught).
    result = client.read_data("secret/data/dev")
    assert result == {}

    # Write some data.
    client.write_data("secret/data/dev", {"foo": "bar"})

    # Now reading should return the data.
    result = client.read_data("secret/data/dev")
    assert result == {"foo": "bar"}



