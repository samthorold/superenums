"""Generic enums: type parameters on the variants, and recursive enums."""

import copy
import pickle
from typing import assert_never

import pytest

from superenums import Variant, variants


class Leaf[T](Variant):
    value: T


class Node[T](Variant):
    left: "Tree[T]"
    right: "Tree[T]"


class Empty(Variant): ...


type Tree[T] = Leaf[T] | Node[T] | Empty


def total(tree: Tree[int]) -> int:
    match tree:
        case Leaf(value=v):
            return v
        case Node(left=left, right=right):
            return total(left) + total(right)
        case Empty():
            return 0
        case _:
            assert_never(tree)


def test_a_recursive_generic_enum_constructs_and_matches() -> None:
    tree = Node(Leaf(1), Node(Leaf(2), Empty()))
    assert total(tree) == 3
    assert repr(Leaf(1)) == "Leaf(value=1)"


def test_a_generic_alias_lists_its_variants_without_type_arguments() -> None:
    assert variants(Tree) == (Leaf, Node, Empty)


class Full[T](Variant):
    value: T


type IntBox = Full[int] | Empty
type Wrapper[T] = Full[T]


def test_an_alias_with_concrete_type_arguments_lists_its_variants() -> None:
    assert variants(IntBox) == (Full, Empty)


def test_an_alias_naming_a_single_generic_variant_lists_it() -> None:
    assert variants(Wrapper) == (Full,)


def test_a_subscripted_generic_variant_constructs_the_plain_variant() -> None:
    leaf = Leaf[int](1)
    assert type(leaf) is Leaf
    assert leaf == Leaf(1)


@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_a_generic_recursive_value_survives_pickling(protocol: int) -> None:
    tree = Node(Leaf[int](1), Empty())
    restored = pickle.loads(pickle.dumps(tree, protocol))
    assert restored == tree
    assert restored.right is Empty()
    assert copy.deepcopy(tree) == tree
