import dataclasses
from typing import Any, assert_type

import shapes
import trees
from shapes import Shape
from trees import Tree

from superenums import Variant, variant_name, variants


def introspection_return_types() -> None:
    assert_type(variants(Shape), tuple[type[Variant], ...])
    assert_type(variant_name(shapes.Empty), str)
    assert_type(variant_name(shapes.Empty()), str)


def generic_variants_are_accepted() -> None:
    assert_type(variants(Tree), tuple[type[Variant], ...])
    assert_type(variant_name(trees.Leaf[int]), str)
    assert_type(variant_name(trees.Leaf(1)), str)


def fields_come_from_dataclasses() -> None:
    assert_type(dataclasses.fields(shapes.Rect), tuple[dataclasses.Field[Any], ...])
    assert_type(
        dataclasses.fields(shapes.Rect(1.0, 2.0)), tuple[dataclasses.Field[Any], ...]
    )


def fields_of_every_variant_of_an_enum() -> None:
    for cls in variants(Shape):
        assert_type(dataclasses.fields(cls), tuple[dataclasses.Field[Any], ...])


def variants_takes_the_alias_not_a_variant() -> None:
    variants(shapes.Circle)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]
