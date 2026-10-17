"""The public, read-only introspection API that extensions build on."""

import dataclasses
from typing import Any

import pytest

from superenums import (
    SuperEnumError,
    Variant,
    Variants,
    alias,
    namespace_of,
    variant_name,
    variants,
)


class Shapes(Variants):
    class Circle(Variant):
        radius: float

    class Rect(Variant):
        w: float
        h: float

    class Empty(Variant): ...


type Shape = Shapes.Circle | Shapes.Rect | Shapes.Empty
Shapes.seal(Shape)


def test_variants_lists_a_namespaces_variants_in_declaration_order() -> None:
    assert variants(Shapes) == (Shapes.Circle, Shapes.Rect, Shapes.Empty)


def test_alias_gives_a_sealed_namespaces_union_alias() -> None:
    assert alias(Shapes) is Shape


def test_alias_of_an_unsealed_namespace_is_refused() -> None:
    class Pets(Variants):
        class Cat(Variant): ...

    with pytest.raises(SuperEnumError, match=r"Pets is not sealed"):
        alias(Pets)


def test_namespace_of_a_variant_class_is_the_namespace_it_was_declared_in() -> None:
    assert namespace_of(Shapes.Circle) is Shapes


def test_namespace_of_a_variant_value_is_its_variants_namespace() -> None:
    assert namespace_of(Shapes.Circle(1.0)) is Shapes
    assert namespace_of(Shapes.Empty()) is Shapes


def test_namespace_of_a_variant_declared_outside_any_namespace_is_refused() -> None:
    class Stray(Variant): ...

    with pytest.raises(
        SuperEnumError, match=r"Stray is declared outside any namespace"
    ):
        namespace_of(Stray)


def test_variant_name_is_the_plain_class_name_of_a_variant_class_or_value() -> None:
    assert variant_name(Shapes.Circle) == "Circle"
    assert variant_name(Shapes.Circle(1.0)) == "Circle"
    assert variant_name(Shapes.Empty()) == "Empty"


def test_fields_come_from_dataclasses_fields_on_variant_classes_and_values() -> None:
    def names(fs: tuple[dataclasses.Field[Any], ...]) -> list[str]:
        return [f.name for f in fs]

    assert names(dataclasses.fields(Shapes.Rect)) == ["w", "h"]
    assert names(dataclasses.fields(Shapes.Rect(1.0, 2.0))) == ["w", "h"]
    assert dataclasses.fields(Shapes.Empty) == ()


def test_variants_named_like_the_introspection_api_do_not_shadow_it() -> None:
    class Words(Variants):
        class Alias(Variant):
            text: str

        class Variants(Variant): ...

    type Word = Words.Alias | Words.Variants
    Words.seal(Word)

    assert variants(Words) == (Words.Alias, Words.Variants)
    assert alias(Words) is Word
    assert namespace_of(Words.Alias("x")) is Words
    assert namespace_of(Words.Variants) is Words
    assert variant_name(Words.Alias) == "Alias"
    assert variant_name(Words.Variants()) == "Variants"


class Trees(Variants):
    class Leaf[T](Variant):
        value: T

    class Node[T](Variant):
        left: "Tree[T]"
        right: "Tree[T]"

    class Empty(Variant): ...


type Tree[T] = Trees.Leaf[T] | Trees.Node[T] | Trees.Empty
Trees.seal(Tree)


def test_introspection_of_a_generic_enum() -> None:
    assert variants(Trees) == (Trees.Leaf, Trees.Node, Trees.Empty)
    assert alias(Trees) is Tree
    leaf = Trees.Leaf[int](1)
    assert namespace_of(leaf) is Trees
    assert namespace_of(Trees.Node(leaf, Trees.Empty())) is Trees
    assert variant_name(leaf) == "Leaf"
    assert [f.name for f in dataclasses.fields(Trees.Node)] == ["left", "right"]


def test_a_subscripted_generic_variant_introspects_as_its_variant() -> None:
    assert namespace_of(Trees.Leaf[int]) is Trees
    assert variant_name(Trees.Leaf[int]) == "Leaf"
