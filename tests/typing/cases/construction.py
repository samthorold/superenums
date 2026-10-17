from dataclasses import KW_ONLY
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


# dataclasses.KW_ONLY makes the fields after it keyword-only, in construction
# and in patterns (they leave __match_args__).


class Events(Variants):
    class Started(Variant):
        _: KW_ONLY
        customer: int
        teller: int


assert_type(Events.Started(customer=1, teller=2), Events.Started)
Events.Started(1, 2)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[missing-argument, too-many-positional-arguments]


def first_customer(event: Events.Started) -> int:
    match event:
        case Events.Started(_, _):  # type: ignore[misc]  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]  # ty: ignore[invalid-match-pattern]
            return 0
        case Events.Started(customer=c):
            return c
