"""The cattrs extension: an enum is written with its tag inside the object."""

import dataclasses
import sys
from typing import Any

import pytest
from cattrs import Converter, UnstructureStrategy

from superenums import SuperEnumError, Variant
from superenums.cattrs import configure


class Circle(Variant):
    radius: float


class Rect(Variant):
    w: float
    h: float


class Empty(Variant): ...


type Shape = Circle | Rect | Empty
type Round = Circle


class Drawing(Variant):
    name: str
    shape: Shape


def converter_for(alias: Any, **kwargs: Any) -> Converter:
    converter = Converter()
    configure(alias, converter, **kwargs)
    return converter


def test_a_value_is_written_with_its_tag_inside_the_object() -> None:
    converter = converter_for(Shape)
    assert converter.unstructure(Circle(1.0), Shape) == {
        "type": "Circle",
        "radius": 1.0,
    }


def test_a_unit_variant_is_written_as_just_its_tag() -> None:
    converter = converter_for(Shape)
    assert converter.unstructure(Empty(), Shape) == {"type": "Empty"}


@pytest.mark.parametrize("value", [Circle(1.0), Rect(1.0, 2.0), Empty()])
def test_every_variant_round_trips(value: Shape) -> None:
    converter = converter_for(Shape)
    assert converter.structure(converter.unstructure(value, Shape), Shape) == value


def test_loading_a_unit_variant_returns_its_one_value() -> None:
    converter = converter_for(Shape)
    assert converter.structure({"type": "Empty"}, Shape) is Empty()


def test_the_tag_key_can_be_changed() -> None:
    converter = converter_for(Shape, key="kind")
    assert converter.unstructure(Empty(), Shape) == {"kind": "Empty"}
    assert converter.structure({"kind": "Circle", "radius": 2.0}, Shape) == Circle(2.0)


def test_a_field_annotated_with_the_alias_is_tagged() -> None:
    converter = converter_for(Shape)
    drawing = Drawing("dot", Circle(1.0))
    data = converter.unstructure(drawing)
    assert data == {"name": "dot", "shape": {"type": "Circle", "radius": 1.0}}
    assert converter.structure(data, Drawing) == drawing


def test_the_union_the_alias_names_is_tagged_too() -> None:
    # cattrs types structure's target as type[T], which an alias isn't; the
    # alias's value (Any to checkers) is the type-checker-friendly spelling.
    converter = converter_for(Shape)
    assert converter.unstructure(Empty(), Shape.__value__) == {"type": "Empty"}
    shape: Shape = converter.structure({"type": "Empty"}, Shape.__value__)
    assert shape is Empty()


def test_an_alias_naming_a_single_variant_is_tagged() -> None:
    converter = converter_for(Round)
    assert converter.unstructure(Circle(1.0), Round) == {
        "type": "Circle",
        "radius": 1.0,
    }
    assert converter.structure({"type": "Circle", "radius": 1.0}, Round) == Circle(1.0)


class Leaf[T](Variant):
    value: T


class Node[T](Variant):
    left: "Tree[T]"
    right: "Tree[T]"


type Tree[T] = Leaf[T] | Node[T] | Empty


@pytest.mark.skipif(
    sys.version_info < (3, 12, 4),
    reason="before 3.12.4, get_type_hints can't see a class's type parameters",
)
def test_a_recursive_generic_enum_round_trips_with_its_type_argument() -> None:
    converter = converter_for(Tree)
    tree = Node(Leaf(1), Node(Leaf(2), Empty()))
    data = converter.unstructure(tree, Tree[int])
    assert data == {
        "type": "Node",
        "left": {"type": "Leaf", "value": 1},
        "right": {
            "type": "Node",
            "left": {"type": "Leaf", "value": 2},
            "right": {"type": "Empty"},
        },
    }
    assert converter.structure(data, Tree[int]) == tree


def test_a_generic_enum_structures_fields_with_its_type_argument() -> None:
    converter = converter_for(Tree)
    assert converter.structure({"type": "Leaf", "value": "3"}, Tree[int]) == Leaf(3)


class Result[T, E](Variant):
    ok: T
    err: E


type Swapped[T, E] = Result[E, T]


def test_type_arguments_follow_the_alias_order_not_the_variant_order() -> None:
    converter = converter_for(Swapped)
    data = {"type": "Result", "ok": "1", "err": 2}
    assert converter.structure(data, Swapped[int, str]) == Result("1", 2)


def _another_empty() -> type[Variant]:
    class Empty(Variant): ...

    return Empty


OtherEmpty = _another_empty()
type Clash = Empty | OtherEmpty  # type: ignore[valid-type]


def test_two_variants_with_the_same_tag_are_refused() -> None:
    with pytest.raises(SuperEnumError, match=r"Clash .* tag 'Empty' more than once"):
        configure(Clash, Converter())


class Typed(Variant):
    type: str


type HasTypeField = Typed | Empty


def test_a_field_named_like_the_tag_key_is_refused() -> None:
    with pytest.raises(SuperEnumError, match=r"Typed has a field named 'type'"):
        configure(HasTypeField, Converter())


def test_a_different_key_avoids_the_clash() -> None:
    converter = converter_for(HasTypeField, key="kind")
    assert converter.unstructure(Typed("x"), HasTypeField) == {
        "kind": "Typed",
        "type": "x",
    }


def test_configuring_something_other_than_an_alias_is_refused() -> None:
    with pytest.raises(SuperEnumError, match="not a type alias"):
        configure(Circle | Empty, Converter())  # type: ignore[arg-type]


def test_loading_an_unknown_tag_fails() -> None:
    converter = converter_for(Shape)
    with pytest.raises(ValueError, match=r"'Hexagon' is not a variant of Shape"):
        converter.structure({"type": "Hexagon"}, Shape)


def test_loading_a_tag_that_is_not_a_string_fails() -> None:
    converter = converter_for(Shape)
    with pytest.raises(ValueError, match=r"\['Circle'\] is not a variant of Shape"):
        converter.structure({"type": ["Circle"]}, Shape)


def test_loading_without_a_tag_fails() -> None:
    converter = converter_for(Shape)
    with pytest.raises(ValueError, match=r"no 'type' key"):
        converter.structure({"radius": 1.0}, Shape)


def test_loading_something_other_than_a_mapping_fails() -> None:
    converter = converter_for(Shape)
    with pytest.raises(TypeError, match="expected a mapping"):
        converter.structure(["Circle", 1.0], Shape)


def test_writing_a_value_of_another_enum_fails() -> None:
    converter = converter_for(Round)
    with pytest.raises(TypeError, match=r"Empty\(\) is not a variant of Round"):
        converter.unstructure(Empty(), Round)


def test_the_tag_is_not_passed_on_to_the_variant() -> None:
    converter = Converter(forbid_extra_keys=True)
    configure(Shape, converter)
    assert converter.structure({"type": "Circle", "radius": 1.0}, Shape) == Circle(1.0)


def test_the_tag_comes_first() -> None:
    converter = converter_for(Shape)
    assert next(iter(converter.unstructure(Rect(1.0, 2.0), Shape))) == "type"


def test_fields_are_written_in_declaration_order() -> None:
    converter = converter_for(Shape)
    data = converter.unstructure(Rect(1.0, 2.0), Shape)
    assert list(data)[1:] == [f.name for f in dataclasses.fields(Rect)]


def test_a_converter_writing_variants_as_tuples_is_refused() -> None:
    converter = Converter(unstruct_strat=UnstructureStrategy.AS_TUPLE)
    configure(Shape, converter)
    with pytest.raises(TypeError, match="needs the dict unstructuring strategy"):
        converter.unstructure(Circle(1.0), Shape)
