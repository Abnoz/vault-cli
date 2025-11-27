from __future__ import annotations

from typing import Any, Dict

import pytest
from typer.testing import CliRunner

from vault_cli import cli


class StubVaultClient:
    def __init__(self, initial: Dict[str, Any] | None = None) -> None:
        self.data = dict(initial or {})

    def read_data(self, path: str) -> Dict[str, Any]:  # noqa: ARG002 - parity with real client
        return dict(self.data)

    def write_data(self, path: str, data: Dict[str, Any]) -> None:  # noqa: ARG002
        self.data = dict(data)


@pytest.fixture(autouse=True)
def reset_cli_context():
    # Typer Context caches objects; ensure clean state between tests.
    cli.app.info.context_settings = {}


def test_list_command_prints_message_when_empty(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(cli, "VaultClient", lambda **_: StubVaultClient({}))
    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "list"],
    )

    assert result.exit_code == 0
    assert "No secrets found." in result.output


def test_set_then_get_roundtrip(monkeypatch):
    runner = CliRunner()
    stub = StubVaultClient({})
    monkeypatch.setattr(cli, "VaultClient", lambda **_: stub)

    set_result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "set", "foo", "123"],
    )
    assert set_result.exit_code == 0
    assert "Successfully added secret 'foo'" in set_result.output

    get_result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "get", "foo"],
    )
    assert get_result.exit_code == 0
    assert "123" in get_result.output


def test_add_fails_when_key_exists(monkeypatch):
    runner = CliRunner()
    stub = StubVaultClient({"foo": "bar"})
    monkeypatch.setattr(cli, "VaultClient", lambda **_: stub)

    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "add", "foo", "baz"],
    )

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_get_missing_key_exits_with_error(monkeypatch):
    runner = CliRunner()
    stub = StubVaultClient({})
    monkeypatch.setattr(cli, "VaultClient", lambda **_: stub)

    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "get", "missing"],
    )

    assert result.exit_code == 1
    assert "not found" in result.output


def test_edit_with_argument_updates_value(monkeypatch):
    runner = CliRunner()
    stub = StubVaultClient({"foo": "old"})
    monkeypatch.setattr(cli, "VaultClient", lambda **_: stub)

    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "edit", "foo", "42"],
    )

    assert result.exit_code == 0
    assert "Successfully updated secret 'foo'" in result.output
    assert stub.data["foo"] == 42  # coerced to int


def test_delete_requires_force_when_non_interactive(monkeypatch):
    runner = CliRunner()
    stub = StubVaultClient({"foo": "bar"})
    monkeypatch.setattr(cli, "VaultClient", lambda **_: stub)

    # Simulate non-interactive stdin by passing input but not --force.
    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "delete", "foo"],
        input="",
    )

    assert result.exit_code == 1
    assert "Use --force to skip confirmation" in result.output


def test_delete_with_force_succeeds_without_prompt(monkeypatch):
    runner = CliRunner()
    stub = StubVaultClient({"foo": "bar"})
    monkeypatch.setattr(cli, "VaultClient", lambda **_: stub)

    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "delete", "foo", "--force"],
    )

    assert result.exit_code == 0
    assert "Successfully deleted secret 'foo'" in result.output
    assert "foo" not in stub.data


def test_set_updates_existing_key(monkeypatch):
    runner = CliRunner()
    stub = StubVaultClient({"foo": 1})
    monkeypatch.setattr(cli, "VaultClient", lambda **_: stub)

    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "set", "foo", "false"],
    )

    assert result.exit_code == 0
    assert "Successfully updated secret 'foo'" in result.output
    assert stub.data["foo"] is False

