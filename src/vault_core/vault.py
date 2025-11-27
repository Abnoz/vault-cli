"""Shared Vault client helpers used by API + CLI layers."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import hvac
from hvac import exceptions as hvac_exceptions
from requests import exceptions as requests_exceptions
import time


class VaultClientError(RuntimeError):
    """Raised when Vault operations fail."""


def _split_kv2_path(full_path: str) -> Tuple[str, str]:
    marker = "/data/"
    if marker not in full_path:
        parts = full_path.split("/", 1)
        if len(parts) == 1:
            raise VaultClientError(
                "Vault path must include KV v2 mount and secret path (e.g. secret/data/dev)",
            )
        return parts[0], parts[1]

    mount, secret_path = full_path.split(marker, 1)
    if not secret_path:
        raise VaultClientError("Vault path must include secret data segment after '/data/'.")

    return mount, secret_path


class VaultClient:
    """Small helper around hvac.Client for KV v2 reads/writes, with retries."""

    def __init__(
        self,
        *,
        addr: str,
        token: str,
        timeout: float = 5.0,
        max_retries: int = 3,
        backoff_seconds: float = 0.2,
    ) -> None:
        self._client = hvac.Client(url=addr, token=token, timeout=timeout)
        self._max_retries = max(1, max_retries)
        self._backoff_seconds = max(0.0, backoff_seconds)

    def _with_retries(self, func, *args, **kwargs):
        """Execute an hvac call with basic retry logic on network/Vault errors."""

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return func(*args, **kwargs)
            except hvac_exceptions.InvalidPath:
                # This is a logical condition, not a transient error; do not retry.
                raise
            except (hvac_exceptions.VaultError, requests_exceptions.RequestException) as exc:
                last_exc = exc
                if attempt >= self._max_retries:
                    break
                time.sleep(self._backoff_seconds * attempt)

        assert last_exc is not None  # for type checkers
        raise VaultClientError("Vault request failed after multiple attempts.") from last_exc

    def read_data(self, path: str) -> Dict[str, Any]:
        mount, secret_path = _split_kv2_path(path)
        try:
            secret = self._with_retries(
                self._client.secrets.kv.v2.read_secret_version,
                mount_point=mount,
                path=secret_path,
            )
        except hvac_exceptions.InvalidPath:
            return {}

        data = secret.get("data", {}).get("data")
        if not isinstance(data, dict):
            return {}
        return data

    def write_data(self, path: str, data: Dict[str, Any]) -> None:
        mount, secret_path = _split_kv2_path(path)
        self._with_retries(
            self._client.secrets.kv.v2.create_or_update_secret,
            mount_point=mount,
            path=secret_path,
            secret=data,
        )

    def list_paths(self, path: str) -> List[str]:
        """List all paths under the given path.

        Args:
            path: Base path to list (e.g., "secret/data/project")

        Returns:
            List of path names (not full paths) under the given path

        Raises:
            VaultClientError: If listing fails
        """
        mount, secret_path = _split_kv2_path(path)
        try:
            response = self._with_retries(
                self._client.secrets.kv.v2.list_secrets,
                mount_point=mount,
                path=secret_path,
            )
            # Response contains 'data' with 'keys' list
            keys = response.get("data", {}).get("keys", [])
            if not isinstance(keys, list):
                return []
            # Remove trailing slashes from keys (hvac returns them)
            return [key.rstrip("/") for key in keys if key]
        except hvac_exceptions.InvalidPath:
            # Path doesn't exist or has no children
            return []

    def delete_data(self, path: str) -> None:
        """Delete a secret path and all its versions.

        Args:
            path: Full path to delete (e.g., "secret/data/project/env")

        Raises:
            VaultClientError: If deletion fails
        """
        mount, secret_path = _split_kv2_path(path)
        self._with_retries(
            self._client.secrets.kv.v2.delete_metadata_and_all_versions,
            mount_point=mount,
            path=secret_path,
        )


