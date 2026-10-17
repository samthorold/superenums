from dataclasses import KW_ONLY
from typing import assert_type

import shapes
from shapes import Shape

from superenums import Variant

# Variant constructors are checked through dataclass_transform, with no plugin.

assert_type(shapes.Circle(1.0), shapes.Circle)
assert_type(shapes.Circle(radius=1.0), shapes.Circle)
assert_type(shapes.Rect(1.0, h=2.0), shapes.Rect)
assert_type(shapes.Empty(), shapes.Empty)

shape: Shape = shapes.Circle(1.0)

shapes.Circle("one")  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]
shapes.Circle()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[missing-argument]
shapes.Circle(diameter=1.0)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[unknown-argument, missing-argument]
shapes.Empty(1.0)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[too-many-positional-arguments]
shapes.Circle(1.0, 2.0)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[too-many-positional-arguments]
shapes.Rect(w=1.0, h="two")  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]


# Field defaults follow dataclass rules: a defaulted field may be omitted.


class Ink(Variant):
    colour: str
    width: float = 0.5


assert_type(Ink("blue"), Ink)
assert_type(Ink("blue", 1.0).width, float)
Ink()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[missing-argument]
Ink("blue", width="wide")  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]


# dataclasses.KW_ONLY makes the fields after it keyword-only, in construction
# and in patterns (they leave __match_args__).


class Started(Variant):
    _: KW_ONLY
    customer: int
    teller: int


assert_type(Started(customer=1, teller=2), Started)
Started(1, 2)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]  # ty: ignore[missing-argument, too-many-positional-arguments]


def first_customer(event: Started) -> int:
    match event:
        case Started(_, _):  # type: ignore[misc]  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]  # ty: ignore[invalid-match-pattern]
            return 0
        case Started(customer=c):
            return c
