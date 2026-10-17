from typing import assert_type

from shapes import Shape, Shapes

from superenums import Variant, Variants

# Variant constructors are checked through dataclass_transform, with no plugin.

assert_type(Shapes.Circle(1.0), Shapes.Circle)
assert_type(Shapes.Circle(radius=1.0), Shapes.Circle)
assert_type(Shapes.Rect(1.0, h=2.0), Shapes.Rect)
assert_type(Shapes.Empty(), Shapes.Empty)

shape: Shape = Shapes.Circle(1.0)

Shapes.Circle("one")  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]
Shapes.Circle()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[missing-argument]
Shapes.Circle(diameter=1.0)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[unknown-argument, missing-argument]
Shapes.Empty(1.0)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[too-many-positional-arguments]
Shapes.Circle(1.0, 2.0)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[too-many-positional-arguments]
Shapes.Rect(w=1.0, h="two")  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]


# Field defaults follow dataclass rules: a defaulted field may be omitted.


class Pens(Variants):
    class Ink(Variant):
        colour: str
        width: float = 0.5


assert_type(Pens.Ink("blue"), Pens.Ink)
assert_type(Pens.Ink("blue", 1.0).width, float)
Pens.Ink()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[missing-argument]
Pens.Ink("blue", width="wide")  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]
