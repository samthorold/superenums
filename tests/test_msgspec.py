"""msgspec through cattrs: msgspec writes the bytes, superenums.cattrs the tags.

There is no superenums.msgspec: msgspec writes every dataclass itself, with no
hook, and refuses a union of them (see the design doc).
"""

import sys
from dataclasses import dataclass

import msgspec
import pytest
from cattrs.preconf.msgspec import make_converter

import superenums.cattrs
from superenums import Variant


class Circle(Variant):
    radius: float


class Empty(Variant): ...


type Shape = Circle | Empty


@dataclass(frozen=True)
class Drawing:
    name: str
    shape: Shape


class Leaf[T](Variant):
    value: T


class Node[T](Variant):
    left: "Tree[T]"
    right: "Tree[T]"


type Tree[T] = Leaf[T] | Node[T] | Empty


def test_a_dataclass_holding_an_enum_round_trips_as_json() -> None:
    converter = make_converter()
    superenums.cattrs.configure(Shape, converter)
    data = converter.dumps(Drawing("dot", Circle(1.0)))
    assert data == b'{"name":"dot","shape":{"type":"Circle","radius":1.0}}'
    assert converter.loads(data, Drawing) == Drawing("dot", Circle(1.0))


def test_an_enum_value_round_trips_as_json() -> None:
    converter = make_converter()
    superenums.cattrs.configure(Shape, converter)
    assert converter.dumps(Empty(), Shape) == b'{"type":"Empty"}'
    assert converter.loads(b'{"type":"Empty"}', Shape.__value__) is Empty()


@pytest.mark.skipif(
    sys.version_info < (3, 12, 4),
    reason="before 3.12.4, get_type_hints can't see a class's type parameters",
)
def test_a_recursive_generic_enum_round_trips_as_json() -> None:
    converter = make_converter()
    superenums.cattrs.configure(Tree, converter)
    tree = Node(Leaf(1), Empty())
    data = converter.dumps(tree, Tree[int])
    assert converter.loads(data, Tree[int]) == tree


class Sketch(msgspec.Struct):
    shape: Shape


def test_a_struct_with_an_enum_field_is_not_supported() -> None:
    # The documented limitation: the converter hands Structs to msgspec, which
    # writes variants as plain dataclasses (dropping the tag, silently) and
    # refuses to read a union of them. If this starts failing, msgspec or
    # cattrs has changed, and the guide's warning should be revisited.
    converter = make_converter()
    superenums.cattrs.configure(Shape, converter)
    assert converter.dumps(Sketch(Empty())) == b'{"shape":{}}'
    with pytest.raises(TypeError, match="may not contain more than one dataclass"):
        converter.loads(b'{"shape": {"type": "Empty"}}', Sketch)
