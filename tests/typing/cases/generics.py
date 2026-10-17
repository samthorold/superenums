from typing import assert_never, assert_type

import trees
from trees import Tree

# ty infers the literal type argument (`Leaf[Literal[1]]`), a subtype of
# `Leaf[int]` because a frozen variant is covariant, so the exact assert_type
# fails in ty only. Assigning to `Tree[int]` works in every checker.
#
# ty narrows a class pattern on a generic variant to the variant with both the
# subject's type argument and `Unknown` (`case trees.Leaf(value=v)` gives
# `v: T | Unknown`), so exact assert_types on narrowed generic values fail in
# ty only. Exhaustiveness is unaffected.


def construction_infers_the_type_argument() -> None:
    assert_type(trees.Leaf(1), trees.Leaf[int])  # ty: ignore[type-assertion-failure]
    assert_type(trees.Leaf("a"), trees.Leaf[str])  # ty: ignore[type-assertion-failure]


def a_recursive_value_fits_its_tree() -> Tree[int]:
    return trees.Node(trees.Leaf(1), trees.Node(trees.Leaf(2), trees.Empty()))


def a_mismatched_type_argument_is_rejected(leaf: trees.Leaf[str]) -> Tree[int]:
    return leaf  # type: ignore[return-value]  # pyright: ignore[reportReturnType]  # ty: ignore[invalid-return-type]


def a_unit_variant_fits_every_tree() -> None:
    ints: Tree[int] = trees.Empty()
    strs: Tree[str] = trees.Empty()
    del ints, strs


def leaves[T](tree: Tree[T]) -> list[T]:
    match tree:
        case trees.Leaf(value=v):
            assert_type(v, T)  # ty: ignore[type-assertion-failure]
            return [v]
        case trees.Node(left=left, right=right):
            assert_type(left, Tree[T])  # ty: ignore[type-assertion-failure]
            return leaves(left) + leaves(right)
        case trees.Empty():
            return []
        case _:
            assert_never(tree)  # pyright: ignore[reportUnreachable]


def a_generic_match_missing_a_variant[T](tree: Tree[T]) -> None:
    match tree:
        case trees.Leaf():
            pass
        case trees.Empty():
            pass
        case _:
            assert_never(tree)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[type-assertion-failure]


def nested_patterns(tree: Tree[int]) -> int:
    match tree:
        case trees.Node(left=trees.Leaf(value=v), right=trees.Empty()):
            assert_type(v, int)  # ty: ignore[type-assertion-failure]
            return v
        case trees.Node(left=trees.Node(left=inner), right=right):
            assert_type(inner, Tree[int])  # ty: ignore[type-assertion-failure]
            assert_type(right, Tree[int])  # ty: ignore[type-assertion-failure]
            return nested_patterns(inner)
        case trees.Leaf(value=v):
            assert_type(v, int)  # ty: ignore[type-assertion-failure]
            return v
        case _:
            return 0
