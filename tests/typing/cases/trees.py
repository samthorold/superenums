"""The generic, recursive enum shared by the case files."""

from superenums import Variant, Variants


class Trees(Variants):
    class Leaf[T](Variant):
        value: T

    class Node[T](Variant):
        left: "Tree[T]"
        right: "Tree[T]"

    class Empty(Variant): ...


type Tree[T] = Trees.Leaf[T] | Trees.Node[T] | Trees.Empty
Trees.seal(Tree)
