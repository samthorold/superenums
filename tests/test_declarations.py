"""Declarations that would let an enum's values go beyond what it declares."""

import dataclasses
from collections.abc import Callable

import pytest

from superenums import SuperEnumError, Variant, Variants


class Shapes(Variants):
    class Circle(Variant):
        radius: float

    class Rect(Variant):
        width: float
        height: float


type Shape = Shapes.Circle | Shapes.Rect
Shapes.seal(Shape)


def test_subclassing_a_variant_raises_when_the_class_is_created() -> None:
    with pytest.raises(SuperEnumError) as excinfo:

        class BigCircle(Shapes.Circle): ...

    message = str(excinfo.value)
    assert "BigCircle" in message
    assert "Shapes.Circle" in message
    assert "subclass" in message


def test_inheriting_from_two_variants_at_once_raises() -> None:
    with pytest.raises(SuperEnumError) as excinfo:

        class Both(Shapes.Circle, Shapes.Rect): ...

    message = str(excinfo.value)
    assert "Both" in message
    assert "Shapes.Circle" in message
    assert "Shapes.Rect" in message


def test_subclassing_a_namespace_raises_when_the_class_is_created() -> None:
    with pytest.raises(SuperEnumError) as excinfo:

        class MoreShapes(Shapes):
            class Triangle(Variant): ...

    message = str(excinfo.value)
    assert "MoreShapes" in message
    assert "Shapes" in message
    assert "subclass" in message


def test_a_generic_variant_subclasses_variant_directly() -> None:
    # PEP 695 adds Generic as a second base; that is still direct subclassing.
    class Boxes(Variants):
        class Full[T](Variant):
            item: T

    assert issubclass(Boxes.Full, Variant)
    assert "item" in Boxes.Full.__dataclass_fields__


def test_a_variant_declaring_its_own_slots_is_rejected() -> None:
    with pytest.raises(SuperEnumError) as excinfo:

        class Pets(Variants):
            class Cat(Variant):
                __slots__ = ("name",)

    message = str(excinfo.value)
    assert "Cat" in message
    assert "__slots__" in message


def test_a_variant_passing_class_keywords_is_rejected() -> None:
    with pytest.raises(SuperEnumError) as excinfo:

        class Pets(Variants):
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

        class Pets(Variants):
            @decorator
            class Cat(Variant):
                name: str

    message = str(excinfo.value)
    assert "Cat" in message
    assert "@dataclass" in message
