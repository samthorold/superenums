"""The core: variants, and introspection of the enums they make.

An enum is a ``type`` alias listing its variants (``type Shape = Circle |
Empty``). The library keeps no registry of enums: everything it knows about
one starts from its alias.
"""

import types
import typing
from collections.abc import Iterable
from dataclasses import FrozenInstanceError, dataclass, fields
from typing import Any, NoReturn, TypeAliasType, dataclass_transform


class SuperEnumError(TypeError):
    """An enum is declared or used in a way superenums does not allow.

    A ``TypeError``, like Python's own errors for a misdeclared class or a
    write to an immutable type.
    """


# Marks a variant class while superenums makes it a dataclass, including the
# class dataclass(slots=True) rebuilds from it.
_BUILDING = "__superenums_building__"


class _VariantMeta(type):
    """Makes each variant class a frozen, slotted dataclass as it is created.

    ``dataclass(slots=True)`` builds a new class rather than changing the one
    it is given, so it runs here, before the class is returned and bound to
    its name. Each variant is then a single class object: the one its module
    holds and its enum's alias names.
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
        type.__setattr__(slotted, "__setattr__", _refuse_write)
        type.__setattr__(slotted, "__delattr__", _refuse_write)
        if _is_unit(slotted):
            _cache_unit(slotted)
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
            "its alias lists"
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


def _refuse_write(self: object, name: str, *value: object) -> NoReturn:
    """Every variant value is frozen: no attribute can be set or deleted.

    Replaces dataclass's frozen ``__setattr__``/``__delattr__``, which for a
    slotted class raise a bare ``TypeError`` (not ``FrozenInstanceError``) on
    a name that is not a field. ``typing``'s subscripted call
    (``Leaf[int](1)``) sets ``__orig_class__`` on the new value and tolerates
    only an ``AttributeError``.
    """
    raise FrozenInstanceError(
        f"{type(self).__qualname__} is frozen: cannot assign to or delete {name!r}"
    )


@dataclass_transform(frozen_default=True)
class Variant(metaclass=_VariantMeta):
    """Base class for a variant: one alternative of an enum."""

    __slots__ = ()


def _is_unit(variant: type[Any]) -> bool:
    """Whether a variant has no fields (defaulted fields still count)."""
    return not fields(variant)


def _cache_unit(variant: type[Any]) -> None:
    """Give a unit variant (one with no fields) exactly one value.

    Its ``__new__`` returns the one cached instance, so calling it and
    ``dataclasses.replace`` give back that instance. Pickle and copy are told
    to rebuild a unit value by calling its class (``__reduce__``) rather than
    through ``object.__new__``, which the older pickle protocols use directly,
    so they give back the same instance too.
    """
    instance: object = object.__new__(variant)

    def __new__(cls: type) -> object:
        return instance

    def __reduce__(self: object) -> tuple[type, tuple[()]]:
        return variant, ()

    type.__setattr__(variant, "__new__", staticmethod(__new__))
    type.__setattr__(variant, "__reduce__", __reduce__)


def _alias_members(alias: TypeAliasType) -> tuple[object, ...]:
    """The members of a union alias (or the single type it names).

    A subscripted generic variant (``Leaf[T]``, ``Leaf[int]``) counts as its
    variant class: type arguments are the checker's to verify.
    """
    value: object = alias.__value__
    if typing.get_origin(value) in (types.UnionType, typing.Union):
        members = typing.get_args(value)
    else:
        members = (value,)
    return tuple(typing.get_origin(m) or m for m in members)


def _names(members: Iterable[object]) -> str:
    return ", ".join(
        m.__qualname__ if isinstance(m, type) else repr(m) for m in members
    )


# Introspection: the public, read-only description of an enum that extensions
# build on. Module-level functions, not attributes on variant classes, so no
# variant's field can shadow them. A variant's fields are the standard
# dataclasses.fields.


def variants(alias: TypeAliasType) -> tuple[type[Variant], ...]:
    """An enum's variants, in the order its alias lists them.

    Raises ``SuperEnumError`` if the alias names anything that is not a
    variant class.
    """
    # Checked at runtime too: untyped callers may pass a class or a union.
    given = typing.cast(object, alias)
    if not isinstance(given, TypeAliasType):
        raise SuperEnumError(
            f"{given!r} is not a type alias: an enum is a `type` statement "
            "listing its variants (type Shape = Circle | Rect)"
        )
    members = _alias_members(given)
    others: list[object] = [
        m for m in members if not (isinstance(m, type) and issubclass(m, Variant))
    ]
    if others:
        raise SuperEnumError(
            f"{alias.__name__} lists {_names(others)}, which "
            f"{'is not a variant' if len(others) == 1 else 'are not variants'}: "
            "an enum's alias lists only Variant subclasses"
        )
    return typing.cast(tuple[type[Variant], ...], members)


def variant_name(variant: type[Variant] | Variant) -> str:
    """A variant's name: its plain class name (``"Circle"``), for a variant
    class or a variant value."""
    return _variant_class(variant).__name__


def _variant_class(variant: object) -> type:
    """The variant class of a variant class, value, or subscripted generic
    variant (``Leaf[int]``)."""
    if isinstance(variant, type):
        return variant
    if isinstance(origin := typing.get_origin(variant), type):
        return origin
    return type(variant)
