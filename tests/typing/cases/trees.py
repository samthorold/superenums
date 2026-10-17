"""The generic, recursive enum shared by the case files: `trees.Leaf`."""

from superenums import Variant


class Leaf[T](Variant):
    value: T


class Node[T](Variant):
    left: "Tree[T]"
    right: "Tree[T]"


class Empty(Variant): ...


type Tree[T] = Leaf[T] | Node[T] | Empty
