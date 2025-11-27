from vault_core.schema import (
    SchemaDocument,
    SecretField,
    ValidationResult,
    validate_secrets,
)


def test_validate_secrets_missing_and_extra_keys():
    schema = SchemaDocument(
        fields=[
            SecretField(name="username", type="string", required=True),
            SecretField(name="enabled", type="boolean", required=False),
        ],
    )
    secrets = {"enabled": "not-bool", "unexpected": 1}

    result = validate_secrets(schema=schema, secrets=secrets)
    assert isinstance(result, ValidationResult)
    assert not result.passed
    assert [detail.key for detail in result.missing] == ["username"]
    assert [detail.key for detail in result.extras] == ["unexpected"]
    assert [detail.key for detail in result.type_mismatches] == ["enabled"]


def test_validate_secrets_passes_when_all_good():
    schema = SchemaDocument(
        fields=[
            SecretField(name="username", type="string", required=True),
            SecretField(name="retries", type="integer", required=False),
        ],
    )
    secrets = {"username": "demo", "retries": 3}

    result = validate_secrets(schema=schema, secrets=secrets)

    assert result.passed
    assert result.missing == []
    assert result.type_mismatches == []
    assert result.extras == []

