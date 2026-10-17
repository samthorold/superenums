"""The enum shared by the case files, which reach it as a module: `shapes.Circle`."""

from superenums import Variant


class Circle(Variant):
    radius: float


class Rect(Variant):
    w: float
    h: float


class Empty(Variant): ...


type Shape = Circle | Rect | Empty
