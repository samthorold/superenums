from typing import assert_never, assert_type

import shapes
from shapes import Shape

# ty treats variant classes as possibly overlapping (a class could inherit from
# two of them), so it narrows later arms to an intersection such as
# `Rect & ~Circle` and rejects the exact assert_type. pyright and mypy narrow
# to the variant itself.


def keyword_patterns(s: Shape) -> None:
    match s:
        case shapes.Circle(radius=r):
            assert_type(s, shapes.Circle)
            assert_type(r, float)
        case shapes.Rect(w=w, h=h):
            assert_type(s, shapes.Rect)  # ty: ignore[assert-type-unspellable-subtype]
            assert_type(w, float)
            assert_type(h, float)
        case shapes.Empty():
            assert_type(s, shapes.Empty)  # ty: ignore[assert-type-unspellable-subtype]
        case _:
            assert_never(s)  # pyright: ignore[reportUnreachable]


def positional_patterns(s: Shape) -> None:
    match s:
        case shapes.Circle(r):
            assert_type(r, float)
        case shapes.Rect(w, h):
            assert_type(w, float)
            assert_type(h, float)
        case shapes.Empty():
            pass
        case _:
            assert_never(s)  # pyright: ignore[reportUnreachable]


def too_many_positional_subpatterns(s: Shape) -> None:
    match s:
        case shapes.Circle(_, _):  # type: ignore[misc]  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]  # ty: ignore[invalid-match-pattern]
            pass
        case _:
            pass
