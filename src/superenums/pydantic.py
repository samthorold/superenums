"""pydantic support: an enum is written with its tag inside the object.

Nothing needs importing or configuring: a plain ``Shape`` in a model is
written ``{"type": "Circle", "radius": 1.0}``. The tag key is always
``"type"``.

pydantic reads ``__pydantic_config__`` from a dataclass before it collects the
dataclass's validators and serializers, for generic dataclasses too (it never
calls ``__get_pydantic_core_schema__`` on ``Leaf[int]``). The variant
metaclass answers that read by calling ``prepare``, which installs a validator,
a serializer and a JSON Schema hook on ``Variant`` that every variant inherits.

Needs the ``pydantic`` extra (``pip install superenums[pydantic]``).
"""

import dataclasses
import typing
from collections.abc import Mapping
from typing import Any

from pydantic import (
    GetJsonSchemaHandler,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, PydanticCustomError

from superenums._core import SuperEnumError, Variant, variant_name

__all__: list[str] = []

KEY = "type"


class _Tag:
    """The hooks ``prepare`` copies onto ``Variant``, written as methods here
    so they are typed as methods. pydantic finds them through each variant's
    bases."""

    @model_validator(mode="before")
    @classmethod
    def _superenums_read_tag(cls, data: Any) -> Any:
        """Check a mapping's tag names this variant, and drop it for the fields."""
        if not isinstance(data, Mapping):
            return data  # a variant value, or input pydantic will reject
        fields = dict(typing.cast(Mapping[str, Any], data))
        tag = variant_name(typing.cast(type[Variant], cls))
        if fields.pop(KEY, None) != tag:
            raise PydanticCustomError(
                "superenums_tag",
                "{key} must be {tag}",
                {"key": repr(KEY), "tag": repr(tag)},
            )
        return fields

    @model_serializer(mode="wrap")
    def _superenums_write_tag(self, handler: SerializerFunctionWrapHandler) -> Any:
        return {KEY: variant_name(typing.cast(Variant, self)), **handler(self)}

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(schema)
        resolved = handler.resolve_ref_schema(json_schema)
        resolved["properties"] = {
            KEY: {
                "const": variant_name(typing.cast(type[Variant], cls)),
                "type": "string",
            },
            **resolved.get("properties", {}),
        }
        resolved["required"] = [KEY, *resolved.get("required", [])]
        return json_schema


_HOOKS = (
    "_superenums_read_tag",
    "_superenums_write_tag",
    "__get_pydantic_json_schema__",
)


def prepare(cls: type[Variant]) -> None:
    """Ready ``cls`` for pydantic: install the tag on ``Variant`` (once), and
    refuse a field the tag would overwrite."""
    if _HOOKS[0] not in vars(Variant):
        for name in _HOOKS:
            type.__setattr__(Variant, name, vars(_Tag)[name])
    if any(field.name == KEY for field in dataclasses.fields(cls)):
        raise SuperEnumError(
            f"{variant_name(cls)} has a field named {KEY!r}, the tag key, which "
            "the tag would overwrite: rename the field to use it with pydantic"
        )
