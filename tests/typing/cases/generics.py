from typing import assert_never, assert_type

from trees import Tree, Trees

# ty infers the literal type argument (`Leaf[Literal[1]]`), a subtype of
# `Leaf[int]` because a frozen variant is covariant, so the exact assert_type
# fails in ty only. Assigning to `Tree[int]` works in every checker.
#
# ty narrows a class pattern on a generic variant to the variant with both the
# subject's type argument and `Unknown` (`case Trees.Leaf(value=v)` gives
# `v: T | Unknown`), so exact assert_types on narrowed generic values fail in
# ty only. Exhaustiveness is unaffected.


def construction_infers_the_type_argument() -> None:
    assert_type(Trees.Leaf(1), Trees.Leaf[int])  # ty: ignore[type-assertion-failure]
    assert_type(Trees.Leaf("a"), Trees.Leaf[str])  # ty: ignore[type-assertion-failure]


def a_recursive_value_fits_its_tree() -> Tree[int]:
    return Trees.Node(Trees.Leaf(1), Trees.Node(Trees.Leaf(2), Trees.Empty()))


def a_mismatched_type_argument_is_rejected(leaf: Trees.Leaf[str]) -> Tree[int]:
    return leaf  # type: ignore[return-value]  # pyright: ignore[reportReturnType]  # ty: ignore[invalid-return-type]


def a_unit_variant_fits_every_tree() -> None:
    ints: Tree[int] = Trees.Empty()
    strs: Tree[str] = Trees.Empty()
    del ints, strs


def leaves[T](tree: Tree[T]) -> list[T]:
    match tree:
        case Trees.Leaf(value=v):
            assert_type(v, T)  # ty: ignore[type-assertion-failure]
            return [v]
        case Trees.Node(left=left, right=right):
            assert_type(left, Tree[T])  # ty: ignore[type-assertion-failure]
            return leaves(left) + leaves(right)
        case Trees.Empty():
            return []
        case _:
            assert_never(tree)  # pyright: ignore[reportUnreachable]


def a_generic_match_missing_a_variant[T](tree: Tree[T]) -> None:
    match tree:
        case Trees.Leaf():
            pass
        case Trees.Empty():
            pass
        case _:
            assert_never(tree)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[type-assertion-failure]


def nested_patterns(tree: Tree[int]) -> int:
    match tree:
        case Trees.Node(left=Trees.Leaf(value=v), right=Trees.Empty()):
            assert_type(v, int)  # ty: ignore[type-assertion-failure]
            return v
        case Trees.Node(left=Trees.Node(left=inner), right=right):
            assert_type(inner, Tree[int])  # ty: ignore[type-assertion-failure]
            assert_type(right, Tree[int])  # ty: ignore[type-assertion-failure]
            return nested_patterns(inner)
        case Trees.Leaf(value=v):
            assert_type(v, int)  # ty: ignore[type-assertion-failure]
            return v
        case _:
            return 0
