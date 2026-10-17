from shapes import Shapes

circle = Shapes.Circle(1.0)

# Variants are frozen: assigning a field is an error in every checker.
circle.radius = 2.0  # type: ignore[misc]  # pyright: ignore[reportAttributeAccessIssue]  # ty: ignore[invalid-assignment]

# Variants are not ordered.
less = circle < Shapes.Circle(2.0)  # type: ignore[operator]  # pyright: ignore[reportOperatorIssue, reportUnknownVariableType]  # ty: ignore[unsupported-operator]
