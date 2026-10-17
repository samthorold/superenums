"""Generic enums: type parameters on the variants, and recursive enums."""

import copy
import pickle
from typing import assert_never

import pytest

from superenums import SuperEnumError, Variant, Variants


class Trees(Variants):
    class Leaf[T](Variant):
        value: T

    class Node[T](Variant):
        left: "Tree[T]"
        right: "Tree[T]"

    class Empty(Variant): ...


type Tree[T] = Trees.Leaf[T] | Trees.Node[T] | Trees.Empty
Trees.seal(Tree)


def total(tree: Tree[int]) -> int:
    match tree:
        case Trees.Leaf(value=v):
            return v
        case Trees.Node(left=left, right=right):
            return total(left) + total(right)
        case Trees.Empty():
            return 0
        case _:
            assert_never(tree)


def test_a_generic_alias_seals_and_its_variants_construct() -> None:
    class Boxes(Variants):
        class Full[T](Variant):
            value: T

        class Empty(Variant): ...

    type Box[T] = Boxes.Full[T] | Boxes.Empty
    Boxes.seal(Box)
    assert Boxes.Full(1).value == 1
    assert Boxes.Empty() is Boxes.Empty()


def test_a_recursive_generic_enum_constructs_and_matches() -> None:
    tree = Trees.Node(Trees.Leaf(1), Trees.Node(Trees.Leaf(2), Trees.Empty()))
    assert total(tree) == 3
    assert repr(Trees.Leaf(1)) == "Trees.Leaf(value=1)"


def test_seal_names_variants_a_generic_alias_omits_or_lists_extra() -> None:
    class Others(Variants):
        class Pair[A, B](Variant):
            first: A
            second: B

    class Boxes(Variants):
        class Full[T](Variant):
            value: T

        class Empty(Variant): ...

    type Box[T] = Boxes.Full[T] | Others.Pair[T, int]
    with pytest.raises(SuperEnumError) as excinfo:
        Boxes.seal(Box)
    message = str(excinfo.value)
    assert "missing" in message
    assert "Boxes.Empty" in message
    assert "extra" in message
    assert "Others.Pair" in message
    assert "Boxes.Full" not in message
    assert "[" not in message


def test_an_alias_with_concrete_type_arguments_seals() -> None:
    class Boxes(Variants):
        class Full[T](Variant):
            value: T

        class Empty(Variant): ...

    type IntBox = Boxes.Full[int] | Boxes.Empty
    Boxes.seal(IntBox)
    assert Boxes.Full(1).value == 1


def test_an_alias_naming_a_single_generic_variant_seals() -> None:
    class Wrappers(Variants):
        class Wrapped[T](Variant):
            value: T

    type Wrapper[T] = Wrappers.Wrapped[T]
    Wrappers.seal(Wrapper)
    assert Wrappers.Wrapped("x").value == "x"


def test_a_subscripted_generic_variant_constructs_the_plain_variant() -> None:
    leaf = Trees.Leaf[int](1)
    assert type(leaf) is Trees.Leaf
    assert leaf == Trees.Leaf(1)


def test_a_subscripted_variant_of_an_unsealed_namespace_says_to_add_seal() -> None:
    class Boxes(Variants):
        class Full[T](Variant):
            value: T

    with pytest.raises(SuperEnumError, match=r"Boxes is not sealed"):
        Boxes.Full[int](1)


@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_a_generic_recursive_value_survives_pickling(protocol: int) -> None:
    tree = Trees.Node(Trees.Leaf[int](1), Trees.Empty())
    restored = pickle.loads(pickle.dumps(tree, protocol))
    assert restored == tree
    assert restored.right is Trees.Empty()
    assert copy.deepcopy(tree) == tree
