"""Unit variants: a variant with no fields has exactly one value.

The variants live at module level so pickle can find them by qualified name.
"""

import copy
import dataclasses
import pickle
import types
from collections.abc import Callable

import pytest

from superenums import Variant


class Circle(Variant):
    radius: float


class Empty(Variant): ...


type Shape = Circle | Empty


def test_calling_a_unit_variant_always_returns_the_same_value() -> None:
    assert Empty() is Empty()


def _pickled(protocol: int) -> Callable[[object], object]:
    def round_trip(value: object) -> object:
        return pickle.loads(pickle.dumps(value, protocol))

    return round_trip


# Every way of duplicating a value: copy, deepcopy, and a pickle round trip in
# each protocol (0 and 1 rebuild objects differently from 2 and later).
duplicates = pytest.mark.parametrize(
    "duplicate",
    [
        pytest.param(copy.copy, id="copy"),
        pytest.param(copy.deepcopy, id="deepcopy"),
        *(
            pytest.param(_pickled(protocol), id=f"pickle-{protocol}")
            for protocol in range(pickle.HIGHEST_PROTOCOL + 1)
        ),
    ],
)


@duplicates
def test_a_duplicated_unit_value_is_the_same_value(
    duplicate: Callable[[object], object],
) -> None:
    empty = Empty()
    assert duplicate(empty) is empty


@duplicates
def test_a_duplicated_variant_with_fields_is_an_equal_value(
    duplicate: Callable[[object], object],
) -> None:
    circle = Circle(radius=2.0)
    duplicated = duplicate(circle)
    assert duplicated == circle
    assert type(duplicated) is Circle


def test_replacing_a_unit_value_gives_back_the_same_value() -> None:
    empty = Empty()
    assert dataclasses.replace(empty) is empty


def test_a_variant_whose_fields_all_have_defaults_is_not_a_unit_variant() -> None:
    class Box(Variant):
        side: float = 1.0

    assert Box() == Box()
    assert Box() is not Box()
    assert Box(side=2.0).side == 2.0


def test_a_unit_variant_refuses_arguments() -> None:
    with pytest.raises(TypeError):
        Empty(1)  # type: ignore[call-arg]


def test_a_unit_pattern_without_parentheses_never_matches_a_unit_value() -> None:
    # The documented trap: `case shapes.Empty:` (a dotted name) is a value
    # pattern comparing against the class itself, not a class pattern.
    shapes = types.SimpleNamespace(Empty=Empty)  # stands in for the module
    match Empty():
        case shapes.Empty:
            matched = True
        case _:
            matched = False
    assert not matched
