from typing import assert_type

from shapes import Shape, Shapes

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
