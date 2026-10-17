"""Matching several enums at once: a tuple subject, as in a transition table.

pyright and ty narrow each element of the tuple, so a complete set of arms is
exhaustive and a missing combination is reported. mypy doesn't narrow a tuple
of unions: it reports even a complete match. Nested matches, one enum at a
time, are checked by all three.
"""

from typing import assert_never

from superenums import Variant


class Idle(Variant): ...


class Busy(Variant):
    job: int


type State = Idle | Busy


class Start(Variant):
    job: int


class Finish(Variant): ...


type Event = Start | Finish


def tuple_complete(s: State, e: Event) -> State:
    match (s, e):
        case (Idle(), Start(job=j)):
            return Busy(j)
        case (Idle(), Finish()):
            return s
        case (Busy(), Start()):
            return s
        case (Busy(), Finish()):
            return Idle()
        case _:
            assert_never((s, e))  # type: ignore[arg-type]  # pyright: ignore[reportUnreachable]


def tuple_missing_a_combination(s: State, e: Event) -> State:
    match (s, e):
        case (Idle(), Start(job=j)):
            return Busy(j)
        case (Idle(), Finish()):
            return s
        case (Busy(), Start()):
            return s
        case _:
            assert_never((s, e))  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # ty: ignore[type-assertion-failure]


def nested_complete(s: State, e: Event) -> State:
    match s:
        case Idle():
            match e:
                case Start(job=j):
                    return Busy(j)
                case Finish():
                    return s
                case _:
                    assert_never(e)  # pyright: ignore[reportUnreachable]
        case Busy():
            match e:
                case Start():
                    return s
                case Finish():
                    return Idle()
                case _:
                    assert_never(e)  # pyright: ignore[reportUnreachable]
        case _:
            assert_never(s)  # pyright: ignore[reportUnreachable]
