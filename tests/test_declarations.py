"""Declarations that would let an enum's values go beyond what it declares."""

import dataclasses
from collections.abc import Callable

import pytest

from superenums import SuperEnumError, Variant


class Circle(Variant):
    radius: float


class Rect(Variant):
    width: float
    height: float


type Shape = Circle | Rect


def test_subclassing_a_variant_raises_when_the_class_is_created() -> None:
    with pytest.raises(SuperEnumError) as excinfo:

        class BigCircle(Circle): ...

    message = str(excinfo.value)
    assert "BigCircle" in message
    assert "Circle" in message
    assert "subclass" in message


def test_inheriting_from_two_variants_at_once_raises() -> None:
    with pytest.raises(SuperEnumError) as excinfo:

        class Both(Circle, Rect): ...

    message = str(excinfo.value)
    assert "Both" in message
    assert "Circle" in message
    assert "Rect" in message


def test_a_generic_variant_subclasses_variant_directly() -> None:
    # PEP 695 adds Generic as a second base; that is still direct subclassing.
    class Full[T](Variant):
        item: T

    assert issubclass(Full, Variant)
    assert "item" in Full.__dataclass_fields__


def test_a_variant_declaring_its_own_slots_is_rejected() -> None:
    with pytest.raises(SuperEnumError) as excinfo:

        class Cat(Variant):
            __slots__ = ("name",)

    message = str(excinfo.value)
    assert "Cat" in message
    assert "__slots__" in message


def test_a_variant_passing_class_keywords_is_rejected() -> None:
    with pytest.raises(SuperEnumError) as excinfo:

        class Cat(Variant, frozen=False):
            name: str

    message = str(excinfo.value)
    assert "Cat" in message
    assert "frozen" in message


@pytest.mark.parametrize("method", ["__setattr__", "__delattr__"])
def test_a_variant_defining_its_own_attribute_writes_is_rejected(method: str) -> None:
    def write(self: object, *args: object) -> None: ...

    with pytest.raises(SuperEnumError) as excinfo:
        type("Cat", (Variant,), {method: write})

    message = str(excinfo.value)
    assert "Cat" in message
    assert method in message
    assert "frozen" in message


@pytest.mark.parametrize(
    "decorator",
    [
        dataclasses.dataclass,
        dataclasses.dataclass(frozen=False),
        dataclasses.dataclass(frozen=True, slots=True),
    ],
    ids=["plain", "unfrozen", "frozen-slotted"],
)
def test_a_variant_applying_dataclass_itself_is_rejected(
    decorator: Callable[[type], type],
) -> None:
    with pytest.raises(SuperEnumError) as excinfo:

        @decorator
        class Cat(Variant):
            name: str

    message = str(excinfo.value)
    assert "Cat" in message
    assert "@dataclass" in message
