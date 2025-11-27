from vault_cli.types import coerce_value


def test_coerce_value_integer():
    assert coerce_value("42") == 42
    assert coerce_value("-7") == -7


def test_coerce_value_boolean():
    assert coerce_value("true") is True
    assert coerce_value("FALSE") is False


def test_coerce_value_preserves_strings():
    assert coerce_value("hello") == "hello"
    assert coerce_value("  spaced  ") == "spaced"
    assert coerce_value("") == ""
