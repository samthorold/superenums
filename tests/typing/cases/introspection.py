import dataclasses
from typing import Any, TypeAliasType, assert_type

from shapes import Shapes
from trees import Trees

from superenums import Variant, Variants, alias, namespace_of, variant_name, variants


def introspection_return_types() -> None:
    assert_type(variants(Shapes), tuple[type[Variant], ...])
    assert_type(alias(Shapes), TypeAliasType)
    assert_type(namespace_of(Shapes.Circle), type[Variants])
    assert_type(namespace_of(Shapes.Circle(1.0)), type[Variants])
    assert_type(variant_name(Shapes.Empty), str)
    assert_type(variant_name(Shapes.Empty()), str)


def generic_variants_are_accepted() -> None:
    assert_type(namespace_of(Trees.Leaf[int]), type[Variants])
    assert_type(variant_name(Trees.Leaf(1)), str)
    assert_type(variants(Trees), tuple[type[Variant], ...])


def fields_come_from_dataclasses() -> None:
    assert_type(dataclasses.fields(Shapes.Rect), tuple[dataclasses.Field[Any], ...])
    assert_type(
        dataclasses.fields(Shapes.Rect(1.0, 2.0)), tuple[dataclasses.Field[Any], ...]
    )


def a_namespace_is_not_a_variant() -> None:
    namespace_of(Shapes)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]


def a_variant_is_not_a_namespace() -> None:
    variants(Shapes.Circle)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]
