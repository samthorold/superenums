import dataclasses
from typing import assert_never

import pytest

from superenums import Variant


class Circle(Variant):
    radius: float


class Empty(Variant): ...


type Shape = Circle | Empty


def describe(s: Shape) -> str:
    match s:
        case Circle(radius=r):
            return f"circle {r}"
        case Empty():
            return "empty"
        case _:
            assert_never(s)


def test_an_enum_matches_each_variant_by_keyword_pattern() -> None:
    assert describe(Circle(radius=2.0)) == "circle 2.0"
    assert describe(Empty()) == "empty"


def test_variants_construct_positionally_and_match_positional_patterns() -> None:
    match Circle(3.0):
        case Circle(r):
            assert r == 3.0
        case _:
            raise AssertionError("positional construction did not match")


def test_a_value_reaching_assert_never_raises() -> None:
    # e.g. a value passed in from unchecked code
    with pytest.raises(AssertionError, match="not a shape"):
        describe("not a shape")  # type: ignore[arg-type]


def test_a_variant_value_rejects_an_undeclared_attribute() -> None:
    circle = Circle(1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        circle.colour = "red"  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        object.__setattr__(circle, "colour", "red")


def test_a_slotted_variant_is_the_class_its_name_is_bound_to() -> None:
    class Cat(Variant):
        name: str

    assert type(Cat("Tom")) is Cat


def test_variants_grouped_in_a_plain_class_still_work() -> None:
    class Pets:
        class Cat(Variant):
            name: str

        bound_in_body = Cat

    assert Pets.bound_in_body is Pets.Cat
    assert Pets.Cat("Tom").name == "Tom"
    assert repr(Pets.Cat("Tom")).endswith("Pets.Cat(name='Tom')")


def test_a_variant_value_is_immutable() -> None:
    circle = Circle(1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        circle.radius = 2.0  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        del circle.radius
    assert circle.radius == 1.0


def test_kw_only_marks_the_fields_after_it_keyword_only() -> None:
    class Started(Variant):
        _: dataclasses.KW_ONLY
        customer: int
        teller: int

    class Mixed(Variant):
        kind: str
        _: dataclasses.KW_ONLY
        customer: int

    started = Started(customer=1, teller=2)
    assert [f.name for f in dataclasses.fields(started)] == ["customer", "teller"]
    with pytest.raises(TypeError, match="positional"):
        Started(1, 2)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]
    assert Mixed("walk-in", customer=3).kind == "walk-in"

    # Keyword-only fields leave __match_args__, so patterns name them too.
    assert Started.__match_args__ == ()
    assert Mixed.__match_args__ == ("kind",)
    match started:
        case Started(customer=c, teller=t):
            assert (c, t) == (1, 2)
        case _:
            raise AssertionError("keyword pattern did not match")


def test_field_defaults_follow_dataclass_rules() -> None:
    class Ink(Variant):
        colour: str
        width: float = 0.5
        tags: list[str] = dataclasses.field(default_factory=list[str])

    ink = Ink("blue")
    assert (ink.width, ink.tags) == (0.5, [])
    assert Ink("red", 1.0).width == 1.0
    assert ink.tags is not Ink("blue").tags

    with pytest.raises(TypeError, match="non-default argument"):

        class Bad(Variant):
            width: float = 0.5
            colour: str  # pyright: ignore[reportGeneralTypeIssues]


def test_values_compare_and_hash_by_variant_and_field_values() -> None:
    class Up(Variant):
        steps: int

    class Down(Variant):
        steps: int

    assert Up(1) == Up(1)
    assert hash(Up(1)) == hash(Up(1))
    assert Up(1) != Up(2)
    assert Up(1) != Down(1)
    assert {Up(1), Up(1), Down(1)} == {Up(1), Down(1)}
    assert {Up(1): "up"}[Up(1)] == "up"
    assert Down(1) not in {Up(1): "up"}


def test_repr_uses_the_qualified_name() -> None:
    assert repr(Circle(radius=1.0)) == "Circle(radius=1.0)"
    assert repr(Empty()) == "Empty()"


def test_replace_returns_a_new_value_of_the_same_variant() -> None:
    circle = Circle(1.0)
    bigger = dataclasses.replace(circle, radius=2.0)
    assert type(bigger) is Circle
    assert bigger == Circle(2.0)
    assert circle == Circle(1.0)


def test_variants_are_not_ordered() -> None:
    with pytest.raises(TypeError):
        Circle(1.0) < Circle(2.0)  # type: ignore[operator]  # noqa: B015
