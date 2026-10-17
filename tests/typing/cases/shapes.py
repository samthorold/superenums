"""The enum shared by the case files."""

from superenums import Variant, Variants


class Shapes(Variants):
    class Circle(Variant):
        radius: float

    class Rect(Variant):
        w: float
        h: float

    class Empty(Variant): ...


type Shape = Shapes.Circle | Shapes.Rect | Shapes.Empty
Shapes.seal(Shape)
