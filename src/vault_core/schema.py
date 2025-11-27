"""Schema models and validation helpers shared across services."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Literal, Mapping, Sequence

from pydantic import BaseModel, Field, ValidationError, model_validator


SecretType = Literal["string", "integer", "boolean", "float"]


class SecretField(BaseModel):
    name: str = Field(..., min_length=1)
    type: SecretType
    required: bool = False
    description: str | None = None


class SchemaDocument(BaseModel):
    fields: List[SecretField] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ensure_unique_names(self) -> "SchemaDocument":
        names = [field.name for field in self.fields]
        if len(set(names)) != len(names):
            raise ValidationError("Schema contains duplicate field names.", SchemaDocument)
        return self

    def field_map(self) -> Dict[str, SecretField]:
        return {field.name: field for field in self.fields}


class ValidationDetail(BaseModel):
    key: str
    expected: SecretType | None = None
    actual: str | None = None
    message: str


class ValidationResult(BaseModel):
    passed: bool
    missing: List[ValidationDetail] = Field(default_factory=list)
    type_mismatches: List[ValidationDetail] = Field(default_factory=list)
    extras: List[ValidationDetail] = Field(default_factory=list)

    @property
    def total_checked(self) -> int:
        return len(self.missing) + len(self.type_mismatches) + len(self.extras)


def _describe_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    return "string"


def _matches_type(expected: SecretType, value: Any) -> bool:
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "float":
        return isinstance(value, (float, int)) and not isinstance(value, bool)
    return isinstance(value, str)


def validate_secrets(
    *,
    schema: SchemaDocument,
    secrets: Mapping[str, Any],
) -> ValidationResult:
    field_map = schema.field_map()
    missing: List[ValidationDetail] = []
    mismatches: List[ValidationDetail] = []
    extras: List[ValidationDetail] = []

    for field in schema.fields:
        if field.required and field.name not in secrets:
            missing.append(
                ValidationDetail(
                    key=field.name,
                    expected=field.type,
                    message="Required field missing",
                ),
            )

    for key, value in secrets.items():
        field = field_map.get(key)
        if field is None:
            extras.append(
                ValidationDetail(
                    key=key,
                    actual=_describe_type(value),
                    message="No schema entry for key",
                ),
            )
            continue

        if not _matches_type(field.type, value):
            mismatches.append(
                ValidationDetail(
                    key=key,
                    expected=field.type,
                    actual=_describe_type(value),
                    message="Type mismatch",
                ),
            )

    passed = not missing and not mismatches
    return ValidationResult(
        passed=passed,
        missing=missing,
        type_mismatches=mismatches,
        extras=extras,
    )


