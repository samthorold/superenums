"""The core: variants, namespaces, and sealing.

Library state about a namespace lives in module-level registries, not in
attributes on the namespace, so it can never collide with the name of a
variant the user declares.
"""

import types
import typing
from collections.abc import Callable, Iterable
from dataclasses import dataclass, fields
from typing import Any, NoReturn, TypeAliasType, dataclass_transform
from weakref import WeakKeyDictionary


class SuperEnumError(TypeError):
    """An enum is declared or used in a way superenums does not allow.

    A ``TypeError``, like Python's own errors for a misdeclared class or a
    write to an immutable type.
    """


# Each namespace's variants, in declaration order.
_variants: WeakKeyDictionary[type["Variants"], tuple[type["Variant"], ...]] = (
    WeakKeyDictionary()
)

# The namespace each variant was declared in.
_namespace_of: WeakKeyDictionary[type, type["Variants"]] = WeakKeyDictionary()

# Each sealed namespace's alias.
_sealed: WeakKeyDictionary[type, TypeAliasType] = WeakKeyDictionary()

# Each variant's dataclass __init__, held back until its namespace is sealed.
_inits: WeakKeyDictionary[type, Callable[..., None]] = WeakKeyDictionary()


# Marks a variant class while superenums makes it a dataclass, including the
# class dataclass(slots=True) rebuilds from it.
_BUILDING = "__superenums_building__"


class _VariantMeta(type):
    """Makes each variant class a frozen, slotted dataclass as it is created.

    ``dataclass(slots=True)`` builds a new class rather than changing the one
    it is given, so it runs here, before the class is returned and bound in
    the namespace body. Each variant is then a single class object: the one
    the namespace collects, the alias names, and ``seal`` compares.
    """

    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> "_VariantMeta":
        # dataclass rebuilding the slotted class through this metaclass:
        # return it as built.
        if _BUILDING in namespace:
            return super().__new__(mcls, name, bases, namespace)
        if bases:
            _check_declaration(name, bases, namespace, kwargs)
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        # Variant itself is not a dataclass.
        if not bases:
            return cls
        # The marker is copied into the namespace dataclass rebuilds the
        # slotted class from, which is how the rebuild is told apart.
        type.__setattr__(cls, _BUILDING, True)
        slotted: type[Any] = dataclass(frozen=True, slots=True)(cls)
        type.__delattr__(slotted, _BUILDING)
        # Construction is refused until the namespace is sealed. Seal puts
        # the dataclass __init__ back, so a sealed variant costs nothing
        # extra to construct. (Guarding __new__ instead would not work:
        # deleting a __new__ from a class does not restore object.__new__'s
        # argument handling.)
        _inits[slotted] = slotted.__init__
        slotted.__init__ = _refuse_unsealed
        return typing.cast(_VariantMeta, slotted)

    def __setattr__(cls, name: str, value: Any) -> None:
        # dataclass records its options on a class before anything else, so
        # @dataclass applied over a finished variant is refused here, before
        # it changes the class. superenums' own dataclass call runs while the
        # class still carries the building marker.
        if name == "__dataclass_params__" and _BUILDING not in vars(cls):
            raise SuperEnumError(
                f"{cls.__qualname__} is decorated with @dataclass: a variant is "
                "already a frozen, slotted dataclass, the same for every "
                "variant, so remove the decorator"
            )
        super().__setattr__(name, value)


def _check_declaration(
    name: str,
    bases: tuple[type, ...],
    namespace: dict[str, Any],
    kwargs: dict[str, Any],
) -> None:
    """Refuse a variant declaration that would go beyond what it says.

    Every variant subclasses Variant directly and is the same frozen, slotted
    dataclass, so nothing in its declaration may change that.
    """
    if variants := [b for b in bases if b is not Variant and issubclass(b, Variant)]:
        raise SuperEnumError(
            f"{name} cannot subclass {_names(variants)}: a variant subclasses "
            "Variant directly, so an enum's values are exactly the variants "
            "its declaration lists"
        )
    if kwargs:
        raise SuperEnumError(
            f"{name} passes class keywords ({', '.join(kwargs)}): every "
            "variant is a frozen, slotted dataclass, with no options"
        )
    if overrides := [m for m in ("__setattr__", "__delattr__") if m in namespace]:
        raise SuperEnumError(
            f"{name} defines {', '.join(overrides)}: a variant is frozen, so "
            "its values cannot change after construction"
        )
    if "__slots__" in namespace:
        raise SuperEnumError(
            f"{name} declares __slots__: a variant's slots are exactly its "
            "fields, which superenums declares for it"
        )


def _refuse_unsealed(self: object, *args: object, **kwargs: object) -> NoReturn:
    """Stands in for a variant's __init__ until its namespace is sealed."""
    cls = type(self)
    namespace = _namespace_of.get(cls)
    if namespace is None:
        raise SuperEnumError(
            f"{cls.__qualname__} is declared outside any namespace, so it belongs "
            "to no sealed enum and cannot be constructed: declare it inside a "
            "Variants subclass"
        )
    name = namespace.__qualname__
    raise SuperEnumError(
        f"{name} is not sealed: add {name}.seal(<alias>) right after the "
        f"union alias that lists its variants, before constructing {cls.__qualname__}"
    )


@dataclass_transform(frozen_default=True)
class Variant(metaclass=_VariantMeta):
    """Base class for a variant: one alternative of an enum."""

    __slots__ = ()


class _VariantsMeta(type):
    """Locks a namespace once it is sealed, so its variants stay fixed."""

    def __setattr__(cls, name: str, value: Any) -> None:
        _check_unlocked(cls, name)
        super().__setattr__(name, value)

    def __delattr__(cls, name: str) -> None:
        _check_unlocked(cls, name)
        super().__delattr__(name)


def _check_unlocked(cls: type, name: str) -> None:
    if cls in _sealed:
        raise SuperEnumError(
            f"{cls.__qualname__} is sealed: its attribute {name!r} cannot be "
            "set or deleted"
        )


class Variants(metaclass=_VariantsMeta):
    """Base class for a namespace, which holds an enum's variants."""

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        bases = cls.__bases__
        if namespaces := [
            b for b in bases if b is not Variants and issubclass(b, Variants)
        ]:
            raise SuperEnumError(
                f"{cls.__qualname__} cannot subclass {_names(namespaces)}: a "
                "namespace subclasses Variants directly, so each variant belongs "
                "to exactly one enum"
            )
        # dict.fromkeys: a variant bound under a second name is listed once.
        _variants[cls] = tuple(
            dict.fromkeys(
                value
                for value in vars(cls).values()
                if isinstance(value, type) and issubclass(value, Variant)
            )
        )
        for variant in _variants[cls]:
            _namespace_of[variant] = cls

    @classmethod
    def seal(cls, alias: TypeAliasType) -> None:
        """Connect the namespace to its union alias, making it an enum.

        Checks that the alias lists exactly the namespace's variants, then
        locks the namespace and allows its variants to be constructed.
        """
        if cls in _sealed:
            raise SuperEnumError(f"{cls.__qualname__} is already sealed")
        declared = _variants[cls]
        known: set[object] = set(declared)
        listed = _alias_variants(alias)
        problems: list[str] = []
        if missing := [v for v in declared if v not in listed]:
            problems.append(f"missing {_names(missing)}")
        if extra := [v for v in listed if v not in known]:
            problems.append(f"extra {_names(extra)}")
        if problems:
            raise SuperEnumError(
                f"{alias.__name__} does not list exactly the variants of "
                f"{cls.__qualname__}: {'; '.join(problems)}"
            )
        for variant in declared:
            type.__setattr__(variant, "__init__", _inits.pop(variant))
            if _is_unit(variant):
                _cache_unit(variant)
        _sealed[cls] = alias


def _is_unit(variant: type[Any]) -> bool:
    """Whether a variant has no fields (defaulted fields still count)."""
    return not fields(variant)


def _cache_unit(variant: type[Any]) -> None:
    """Give a unit variant (one with no fields) exactly one value.

    Its ``__new__`` returns the one cached instance, so calling it and
    ``dataclasses.replace`` give back that instance. Pickle and copy are told
    to rebuild a unit value by calling its class (``__reduce__``) rather than
    through ``object.__new__``, which the older pickle protocols use directly,
    so they give back the same instance too. Installed by ``seal``, so an
    unsealed unit variant still refuses construction through the stand-in
    ``__init__``.
    """
    instance: object = object.__new__(variant)

    def __new__(cls: type) -> object:
        return instance

    def __reduce__(self: object) -> tuple[type, tuple[()]]:
        return variant, ()

    type.__setattr__(variant, "__new__", staticmethod(__new__))
    type.__setattr__(variant, "__reduce__", __reduce__)


def _alias_variants(alias: TypeAliasType) -> tuple[object, ...]:
    """The members of a union alias (or the single type it names)."""
    value: object = alias.__value__
    if typing.get_origin(value) in (types.UnionType, typing.Union):
        return typing.get_args(value)
    return (value,)


def _names(members: Iterable[object]) -> str:
    return ", ".join(
        m.__qualname__ if isinstance(m, type) else repr(m) for m in members
    )
