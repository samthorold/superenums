"""pydantic support: a plain alias is written with its tag inside the object.

Nothing is configured or imported: pydantic finds the tag on every variant.
"""

import subprocess
import sys
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError, with_config

from superenums import SuperEnumError, Variant


class Circle(Variant):
    radius: float


class Empty(Variant): ...


class Nothing(Variant): ...


class Celsius(Variant):
    degrees: float


class Fahrenheit(Variant):
    degrees: float


class Sized(Variant):
    size: int = 3


type Shape = Circle | Empty | Nothing
type Temperature = Celsius | Fahrenheit


def test_a_value_is_written_with_its_tag_inside_the_object() -> None:
    adapter = TypeAdapter(Shape)
    assert adapter.dump_python(Circle(1.0)) == {"type": "Circle", "radius": 1.0}


@pytest.mark.parametrize("value", [Circle(1.0), Empty(), Nothing()])
def test_every_variant_round_trips(value: Shape) -> None:
    adapter = TypeAdapter(Shape)
    assert adapter.validate_python(adapter.dump_python(value)) == value
    assert adapter.validate_json(adapter.dump_json(value)) == value


def test_unit_variants_stay_apart_and_load_as_their_one_value() -> None:
    adapter = TypeAdapter(Shape)
    assert adapter.dump_python(Nothing()) == {"type": "Nothing"}
    assert adapter.validate_python({"type": "Nothing"}) is Nothing()
    assert adapter.validate_json('{"type": "Empty"}') is Empty()


def test_variants_with_the_same_fields_stay_apart() -> None:
    adapter = TypeAdapter(Temperature)
    data = adapter.dump_python(Fahrenheit(451.0))
    assert data == {"type": "Fahrenheit", "degrees": 451.0}
    assert adapter.validate_python(data) == Fahrenheit(451.0)


def test_defaults_fill_missing_fields() -> None:
    assert TypeAdapter(Sized).validate_python({"type": "Sized"}) == Sized(3)


def test_a_value_validates_as_itself() -> None:
    circle = Circle(1.0)
    assert TypeAdapter(Shape).validate_python(circle) is circle


class Drawing(BaseModel):
    shape: Shape
    centre: Circle


def test_model_fields_annotated_with_the_alias_or_a_variant_are_tagged() -> None:
    drawing = Drawing(shape=Nothing(), centre=Circle(0.5))
    data = drawing.model_dump()
    assert data == {
        "shape": {"type": "Nothing"},
        "centre": {"type": "Circle", "radius": 0.5},
    }
    assert Drawing.model_validate_json(drawing.model_dump_json()) == drawing


def test_loading_an_unknown_tag_fails() -> None:
    with pytest.raises(ValidationError, match="'type' must be 'Circle'"):
        TypeAdapter(Shape).validate_python({"type": "Hexagon"})


def test_loading_without_a_tag_fails() -> None:
    with pytest.raises(ValidationError, match="'type' must be 'Circle'"):
        TypeAdapter(Circle).validate_python({"radius": 1.0})


def test_the_json_schema_requires_the_tag() -> None:
    schema = TypeAdapter(Shape).json_schema()
    circle = schema["$defs"]["Circle"]
    assert circle["properties"]["type"] == {"const": "Circle", "type": "string"}
    assert circle["required"] == ["type", "radius"]
    assert schema["$defs"]["Empty"]["required"] == ["type"]


class Typed(Variant):
    type: str


def test_a_field_named_like_the_tag_key_is_refused() -> None:
    with pytest.raises(SuperEnumError, match="Typed has a field named 'type'"):
        TypeAdapter(Typed)


@with_config(ConfigDict(strict=True))
class Strict(Variant):
    count: int


class StrictInBody(Variant):
    __pydantic_config__ = ConfigDict(strict=True)
    count: int


@pytest.mark.parametrize("variant", [Strict, StrictInBody])
def test_pydantic_config_on_a_variant_is_honoured(variant: type[Any]) -> None:
    # Strict mode takes only instances from Python input, so check with JSON.
    adapter = TypeAdapter(variant)
    tag = variant.__name__
    assert adapter.validate_json(f'{{"type": "{tag}", "count": 1}}') == variant(1)
    with pytest.raises(ValidationError, match="Input should be a valid integer"):
        adapter.validate_json(f'{{"type": "{tag}", "count": "1"}}')


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
    adapter = TypeAdapter(Tree[int])
    tree = Node(Leaf(1), Node(Leaf(2), Empty()))
    data = adapter.dump_python(tree)
    assert data == {
        "type": "Node",
        "left": {"type": "Leaf", "value": 1},
        "right": {
            "type": "Node",
            "left": {"type": "Leaf", "value": 2},
            "right": {"type": "Empty"},
        },
    }
    assert adapter.validate_python(data) == tree


def test_a_generic_enum_validates_fields_with_its_type_argument() -> None:
    adapter = TypeAdapter(Tree[int])
    assert adapter.validate_python({"type": "Leaf", "value": "3"}) == Leaf(3)


GENERIC_FIRST = """
from pydantic import TypeAdapter
from superenums import Variant

class Loaded[T](Variant):
    value: T

class Pending(Variant): ...

type Fetch[T] = Loaded[T] | Pending

assert TypeAdapter(Fetch[int]).dump_python(Loaded(1)) == {"type": "Loaded", "value": 1}
"""


def test_a_generic_variant_is_tagged_when_pydantic_meets_it_first() -> None:
    # In a fresh interpreter: in this one, earlier tests have set pydantic up.
    result = subprocess.run(
        [sys.executable, "-c", GENERIC_FIRST],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
