from typing import assert_never, assert_type

from shapes import Shape, Shapes

# ty treats variant classes as possibly overlapping (a class could inherit from
# two of them), so it narrows later arms to an intersection such as
# `Rect & ~Circle` and rejects the exact assert_type. pyright and mypy narrow
# to the variant itself.


def keyword_patterns(s: Shape) -> None:
    match s:
        case Shapes.Circle(radius=r):
            assert_type(s, Shapes.Circle)
            assert_type(r, float)
        case Shapes.Rect(w=w, h=h):
            assert_type(s, Shapes.Rect)  # ty: ignore[assert-type-unspellable-subtype]
            assert_type(w, float)
            assert_type(h, float)
        case Shapes.Empty():
            assert_type(s, Shapes.Empty)  # ty: ignore[assert-type-unspellable-subtype]
        case _:
            assert_never(s)  # pyright: ignore[reportUnreachable]


def positional_patterns(s: Shape) -> None:
    match s:
        case Shapes.Circle(r):
            assert_type(r, float)
        case Shapes.Rect(w, h):
            assert_type(w, float)
            assert_type(h, float)
        case Shapes.Empty():
            pass
        case _:
            assert_never(s)  # pyright: ignore[reportUnreachable]


def too_many_positional_subpatterns(s: Shape) -> None:
    match s:
        case Shapes.Circle(_, _):  # type: ignore[misc]  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]  # ty: ignore[invalid-match-pattern]
            pass
        case _:
            pass
