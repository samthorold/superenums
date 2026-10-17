"""The core: variants, namespaces, and sealing.

Library state about a namespace lives in module-level registries, not in
attributes on the namespace, so it can never collide with the name of a
variant the user declares.
"""

import types
import typing
from dataclasses import dataclass
from typing import TypeAliasType, dataclass_transform
from weakref import WeakKeyDictionary


@dataclass_transform(frozen_default=True)
class Variant:
    """Base class for a variant: one alternative of an enum."""

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        dataclass(frozen=True)(cls)


# Each namespace's variants, in declaration order.
_variants: WeakKeyDictionary[type["Variants"], tuple[type[Variant], ...]] = (
    WeakKeyDictionary()
)


class Variants:
    """Base class for a namespace, which holds an enum's variants."""

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        _variants[cls] = tuple(
            value
            for value in vars(cls).values()
            if isinstance(value, type) and issubclass(value, Variant)
        )

    @classmethod
    def seal(cls, alias: TypeAliasType) -> None:
        """Connect the namespace to its union alias.

        The alias must list exactly the namespace's variants.
        """
        if set(_alias_variants(alias)) != set(_variants[cls]):
            raise TypeError(
                f"{alias.__name__} does not list exactly the variants of "
                f"{cls.__qualname__}"
            )


def _alias_variants(alias: TypeAliasType) -> tuple[object, ...]:
    """The members of a union alias (or the single type it names)."""
    value: object = alias.__value__
    if typing.get_origin(value) in (types.UnionType, typing.Union):
        return typing.get_args(value)
    return (value,)
