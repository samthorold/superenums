"""cattrs support: an enum is written with its tag inside the object.

    converter = cattrs.Converter()
    superenums.cattrs.configure(Shape, converter)
    converter.unstructure(Circle(1.0), Shape)  # {"type": "Circle", "radius": 1.0}

Needs the ``cattrs`` extra (``pip install superenums[cattrs]``).
"""

import dataclasses
import types
import typing
from collections.abc import Callable, Mapping
from typing import Any, TypeAliasType

from cattrs import BaseConverter

from superenums._core import SuperEnumError, Variant, variant_name, variants

__all__ = ["configure"]


def configure(
    alias: TypeAliasType, converter: BaseConverter, *, key: str = "type"
) -> None:
    """Make ``converter`` write the enum ``alias`` with its tag inside the object.

    Wherever cattrs un/structures the alias (``converter.structure(data, Shape)``,
    or a field annotated ``Shape``), a value is a mapping of the variant's
    fields plus ``key``, whose value is the variant's name. A generic enum is
    configured once, and each specialisation (``Tree[int]``) is handled. The
    union the alias names (``Shape.__value__``) is handled too: type checkers
    accept it as ``structure``'s target, where they reject the alias.

    Raises ``SuperEnumError`` if two variants share a name, or a variant has a
    field named ``key``.
    """
    classes = variants(alias)
    _check_tags(alias, classes, key)
    value: Any = alias.__value__
    union = value if _is_union(value) else None

    def type_args(cl: Any) -> tuple[Any, ...] | None:
        """The alias's type arguments if ``cl`` is (a specialisation of) the
        alias or its union, else ``None``."""
        if cl is alias or (union is not None and cl == union):
            return ()
        if typing.get_origin(cl) is alias:
            return typing.get_args(cl)
        return None

    def is_alias(cl: Any) -> bool:
        return type_args(cl) is not None

    def unstructure_factory(cl: Any) -> Callable[[Any], dict[str, Any]]:
        return _Tagged(alias, type_args(cl) or (), converter, key).unstructure

    def structure_factory(cl: Any) -> Callable[[Any, Any], Any]:
        return _Tagged(alias, type_args(cl) or (), converter, key).structure

    converter.register_unstructure_hook_factory(is_alias, unstructure_factory)
    converter.register_structure_hook_factory(is_alias, structure_factory)


def _check_tags(
    alias: TypeAliasType, classes: tuple[type[Variant], ...], key: str
) -> None:
    seen: set[str] = set()
    for cls in classes:
        tag = variant_name(cls)
        if tag in seen:
            raise SuperEnumError(
                f"{alias.__name__} lists more than one variant named {tag!r}, so "
                f"it would write the tag {tag!r} more than once: tags must be unique"
            )
        seen.add(tag)
        if any(field.name == key for field in dataclasses.fields(cls)):
            raise SuperEnumError(
                f"{tag} has a field named {key!r}, the tag key, which the tag "
                "would overwrite: configure a different key"
            )


class _Tagged:
    """The hooks for one alias, or one specialisation of a generic alias."""

    def __init__(
        self,
        alias: TypeAliasType,
        args: tuple[Any, ...],
        converter: BaseConverter,
        key: str,
    ) -> None:
        self._alias = alias
        self._converter = converter
        self._key = key
        # Member types (Leaf[int]) by tag and by variant class. Per-variant
        # hooks are fetched on each call (cattrs caches them), not here: a
        # recursive enum's variant hooks need this alias's, still being made.
        self._by_tag: dict[str, Any] = {}
        self._by_class: dict[type, tuple[str, Any]] = {}
        for member in _members(alias, args):
            cls = typing.get_origin(member) or member
            tag = variant_name(cls)
            self._by_tag[tag] = member
            self._by_class[cls] = (tag, member)

    def unstructure(self, value: Any) -> dict[str, Any]:
        found = self._by_class.get(type(typing.cast(object, value)))
        if found is None:
            raise TypeError(f"{value!r} is not a variant of {self._alias.__name__}")
        tag, member = found
        fields = self._converter.get_unstructure_hook(member)(value)
        if not isinstance(fields, Mapping):
            raise TypeError(
                f"the converter wrote {tag} as {type(fields).__name__}, not a "
                "mapping: a tagged enum needs the dict unstructuring strategy"
            )
        return {self._key: tag, **typing.cast(Mapping[str, Any], fields)}

    def structure(self, data: Any, _: Any) -> Any:
        if not isinstance(data, Mapping):
            raise TypeError(
                f"expected a mapping with a {self._key!r} key for "
                f"{self._alias.__name__}, got {type(data).__name__}"
            )
        fields = dict(typing.cast(Mapping[str, Any], data))
        if self._key not in fields:
            raise ValueError(
                f"no {self._key!r} key to say which variant of "
                f"{self._alias.__name__} this is"
            )
        tag = fields.pop(self._key)
        member = self._by_tag.get(tag) if isinstance(tag, str) else None
        if member is None:
            raise ValueError(f"{tag!r} is not a variant of {self._alias.__name__}")
        return self._converter.get_structure_hook(member)(fields, member)


def _members(alias: TypeAliasType, args: tuple[Any, ...]) -> tuple[Any, ...]:
    """The alias's members, with ``args`` substituted for its type parameters."""
    value: Any = alias.__value__
    if args:
        # The value's own parameters can be in a different order from the
        # alias's (type Swapped[T, E] = Result[E, T]): substitute by name.
        bound = dict(zip(alias.__type_params__, args, strict=True))
        params: tuple[Any, ...] = getattr(value, "__parameters__", ())
        if params:
            value = value[tuple(bound[p] for p in params)]
    return typing.get_args(value) if _is_union(value) else (value,)


def _is_union(value: object) -> bool:
    return typing.get_origin(value) in (typing.Union, types.UnionType)
