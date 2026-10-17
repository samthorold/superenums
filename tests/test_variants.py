from typing import assert_never

import pytest

from superenums import Variant, Variants


class Shapes(Variants):
    class Circle(Variant):
        radius: float

    class Empty(Variant): ...


type Shape = Shapes.Circle | Shapes.Empty
Shapes.seal(Shape)


def describe(s: Shape) -> str:
    match s:
        case Shapes.Circle(radius=r):
            return f"circle {r}"
        case Shapes.Empty():
            return "empty"
        case _:
            assert_never(s)


def test_a_sealed_enum_matches_each_variant_by_keyword_pattern() -> None:
    assert describe(Shapes.Circle(radius=2.0)) == "circle 2.0"
    assert describe(Shapes.Empty()) == "empty"


def test_variants_construct_positionally_and_match_positional_patterns() -> None:
    match Shapes.Circle(3.0):
        case Shapes.Circle(r):
            assert r == 3.0
        case _:
            raise AssertionError("positional construction did not match")


def test_a_value_reaching_assert_never_raises() -> None:
    # e.g. a value passed in from unchecked code
    with pytest.raises(AssertionError, match="not a shape"):
        describe("not a shape")  # type: ignore[arg-type]


def test_seal_accepts_an_alias_of_a_single_variant() -> None:
    class Units(Variants):
        class Only(Variant): ...

    type Unit = Units.Only
    Units.seal(Unit)


def test_seal_rejects_an_alias_that_does_not_list_exactly_the_variants() -> None:
    class Pets(Variants):
        class Cat(Variant): ...

        class Dog(Variant): ...

    type Pet = Pets.Cat
    with pytest.raises(TypeError):
        Pets.seal(Pet)
