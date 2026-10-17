"""The public, read-only introspection API that extensions build on."""

import dataclasses
from typing import Any

import pytest

from superenums import SuperEnumError, Variant, variant_name, variants


class Circle(Variant):
    radius: float


class Rect(Variant):
    w: float
    h: float


class Empty(Variant): ...


type Shape = Circle | Rect | Empty
type Round = Circle


def test_variants_lists_an_enums_variants_in_the_order_its_alias_does() -> None:
    assert variants(Shape) == (Circle, Rect, Empty)


def test_variants_of_an_alias_naming_a_single_variant() -> None:
    assert variants(Round) == (Circle,)


class NotAVariant: ...


type Mixed = Circle | NotAVariant | int


def test_variants_refuses_an_alias_listing_anything_but_variants() -> None:
    with pytest.raises(SuperEnumError) as excinfo:
        variants(Mixed)
    message = str(excinfo.value)
    assert "Mixed" in message
    assert "NotAVariant" in message
    assert "int" in message
    assert "Circle," not in message


@pytest.mark.parametrize(
    "given", [Circle, Circle | Rect], ids=["variant class", "bare union"]
)
def test_variants_refuses_anything_but_a_type_alias(given: Any) -> None:
    with pytest.raises(SuperEnumError, match="not a type alias"):
        variants(given)


def test_a_variant_can_be_listed_in_more_than_one_alias() -> None:
    assert Circle in variants(Shape)
    assert Circle in variants(Round)


def test_variant_name_is_the_plain_class_name_of_a_variant_class_or_value() -> None:
    assert variant_name(Circle) == "Circle"
    assert variant_name(Circle(1.0)) == "Circle"
    assert variant_name(Empty()) == "Empty"


def test_fields_come_from_dataclasses_fields_on_variant_classes_and_values() -> None:
    def names(fs: tuple[dataclasses.Field[Any], ...]) -> list[str]:
        return [f.name for f in fs]

    assert names(dataclasses.fields(Rect)) == ["w", "h"]
    assert names(dataclasses.fields(Rect(1.0, 2.0))) == ["w", "h"]
    assert dataclasses.fields(Empty) == ()


class Leaf[T](Variant):
    value: T


def test_a_subscripted_generic_variant_introspects_as_its_variant() -> None:
    assert variant_name(Leaf[int]) == "Leaf"
    assert variant_name(Leaf[int](1)) == "Leaf"
