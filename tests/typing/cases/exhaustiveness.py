from typing import assert_never

from shapes import Shape, Shapes


def complete(s: Shape) -> None:
    match s:
        case Shapes.Circle():
            pass
        case Shapes.Rect():
            pass
        case Shapes.Empty():
            pass
        case _:
            assert_never(s)  # pyright: ignore[reportUnreachable]


def missing_a_variant(s: Shape) -> None:
    match s:
        case Shapes.Circle():
            pass
        case Shapes.Rect():
            pass
        case _:
            assert_never(s)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[type-assertion-failure]


def unit_pattern_without_parentheses(s: Shape) -> None:
    # `case Shapes.Empty:` compares against the class itself, so it never
    # matches a unit value and does not count towards exhaustiveness.
    match s:
        case Shapes.Circle():
            pass
        case Shapes.Rect():
            pass
        case Shapes.Empty:
            pass
        case _:
            assert_never(s)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[type-assertion-failure]
