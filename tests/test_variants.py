import dataclasses
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


def test_a_variant_value_rejects_an_undeclared_attribute() -> None:
    circle = Shapes.Circle(1.0)
    with pytest.raises((AttributeError, TypeError)):
        circle.colour = "red"  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        object.__setattr__(circle, "colour", "red")


def test_a_slotted_variant_is_the_class_the_namespace_body_bound() -> None:
    class Pets(Variants):
        class Cat(Variant):
            name: str

        bound_in_body = Cat

    type Pet = Pets.Cat
    assert Pets.bound_in_body is Pets.Cat
    assert Pet.__value__ is Pets.Cat
    assert type(Pets.Cat("Tom")) is Pets.Cat
    Pets.seal(Pet)


def test_a_variant_value_is_immutable() -> None:
    circle = Shapes.Circle(1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        circle.radius = 2.0  # type: ignore[misc]
    assert circle.radius == 1.0


def test_field_defaults_follow_dataclass_rules() -> None:
    class Pens(Variants):
        class Ink(Variant):
            colour: str
            width: float = 0.5
            tags: list[str] = dataclasses.field(default_factory=list[str])

    ink = Pens.Ink("blue")
    assert (ink.width, ink.tags) == (0.5, [])
    assert Pens.Ink("red", 1.0).width == 1.0
    assert ink.tags is not Pens.Ink("blue").tags

    with pytest.raises(TypeError, match="non-default argument"):

        class Broken(Variants):
            class Bad(Variant):
                width: float = 0.5
                colour: str  # pyright: ignore[reportGeneralTypeIssues]


def test_values_compare_and_hash_by_variant_and_field_values() -> None:
    class Moves(Variants):
        class Up(Variant):
            steps: int

        class Down(Variant):
            steps: int

    assert Moves.Up(1) == Moves.Up(1)
    assert hash(Moves.Up(1)) == hash(Moves.Up(1))
    assert Moves.Up(1) != Moves.Up(2)
    assert Moves.Up(1) != Moves.Down(1)
    assert {Moves.Up(1), Moves.Up(1), Moves.Down(1)} == {Moves.Up(1), Moves.Down(1)}
    assert {Moves.Up(1): "up"}[Moves.Up(1)] == "up"
    assert Moves.Down(1) not in {Moves.Up(1): "up"}


def test_repr_uses_the_qualified_name() -> None:
    assert repr(Shapes.Circle(radius=1.0)) == "Shapes.Circle(radius=1.0)"
    assert repr(Shapes.Empty()) == "Shapes.Empty()"


def test_replace_returns_a_new_value_of_the_same_variant() -> None:
    circle = Shapes.Circle(1.0)
    bigger = dataclasses.replace(circle, radius=2.0)
    assert type(bigger) is Shapes.Circle
    assert bigger == Shapes.Circle(2.0)
    assert circle == Shapes.Circle(1.0)


def test_variants_are_not_ordered() -> None:
    with pytest.raises(TypeError):
        Shapes.Circle(1.0) < Shapes.Circle(2.0)  # type: ignore[operator]  # noqa: B015
