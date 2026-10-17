from typing import assert_never

import shapes
from shapes import Shape


def complete(s: Shape) -> None:
    match s:
        case shapes.Circle():
            pass
        case shapes.Rect():
            pass
        case shapes.Empty():
            pass
        case _:
            assert_never(s)  # pyright: ignore[reportUnreachable]


def missing_a_variant(s: Shape) -> None:
    match s:
        case shapes.Circle():
            pass
        case shapes.Rect():
            pass
        case _:
            assert_never(s)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[type-assertion-failure]


def unit_pattern_without_parentheses(s: Shape) -> None:
    # `case shapes.Empty:` compares against the class itself, so it never
    # matches a unit value and does not count towards exhaustiveness.
    match s:
        case shapes.Circle():
            pass
        case shapes.Rect():
            pass
        case shapes.Empty:
            pass
        case _:
            assert_never(s)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[type-assertion-failure]
