"""Methods written on each variant keep exhaustiveness.

Calling a method on the union type-checks only if every variant defines it, so
a variant without it is reported wherever the method is called on the enum.
"""

from superenums import Variant


class Circle(Variant):
    radius: float

    def area(self) -> float:
        return 3.14 * self.radius**2


class Square(Variant):
    side: float

    def area(self) -> float:
        return self.side**2


class Empty(Variant): ...


type Complete = Circle | Square
type MissingOne = Circle | Square | Empty


def every_variant_defines_it(s: Complete) -> float:
    return s.area()


def one_variant_lacks_it(s: MissingOne) -> float:
    return s.area()  # type: ignore[union-attr]  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownVariableType]  # ty: ignore[unresolved-attribute]
