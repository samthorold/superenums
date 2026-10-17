"""Annotating with the namespace instead of the enum defeats exhaustiveness.

``s: Shapes`` names the namespace class, which is open and is not a base of
its variants. No match over it is proven exhaustive, even one that handles
every variant: every checker reports the ``assert_never`` arm. pyright also
reports (``reportUnnecessaryComparison``, on in strict mode) that each variant
pattern can never match a ``Shapes``, which makes its arm unreachable.
"""

from typing import assert_never

from shapes import Shapes


def annotated_with_the_namespace(s: Shapes) -> None:
    match s:
        case Shapes.Circle():  # pyright: ignore[reportUnnecessaryComparison]
            pass  # pyright: ignore[reportUnreachable]
        case Shapes.Rect():  # pyright: ignore[reportUnnecessaryComparison]
            pass  # pyright: ignore[reportUnreachable]
        case Shapes.Empty():  # pyright: ignore[reportUnnecessaryComparison]
            pass  # pyright: ignore[reportUnreachable]
        case _:
            assert_never(s)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[type-assertion-failure]
