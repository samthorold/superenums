# /// script
# requires-python = ">=3.13"
# dependencies = ["py-ev", "superenums"]
#
# [tool.uv.sources]
# py-ev = { git = "https://github.com/samthorold/py-ev", tag = "v0.1.0" }
# superenums = { path = "..", editable = true }
# ///
"""A bank with a few tellers and one queue, simulated with py-ev.

The simulation's events are one superenums enum, `BankEvent`, used as py-ev's
event type `T`. py-ev broadcasts every event to every process, so each process
is a `match` over the whole enum and the type checker proves it handles every
variant. Adding a variant makes each process decide what to do with it.

Time is in whole minutes from opening. Run it with:

    uv run examples/bank_tellers.py
"""

import random
from collections import deque
from collections.abc import Iterator
from dataclasses import KW_ONLY, dataclass, field
from typing import assert_never

from pyev import EventLoop

from superenums import Variant, Variants


class BankEvents(Variants):
    class CustomerArrived(Variant):
        customer: int

    class ServiceStarted(Variant):
        _: KW_ONLY  # two ints: never positional
        customer: int
        teller: int

    class ServiceFinished(Variant):
        _: KW_ONLY  # two ints: never positional
        customer: int
        teller: int

    class CustomerTurnedAway(Variant):
        customer: int

    class DoorsClosed(Variant): ...


type BankEvent = (
    BankEvents.CustomerArrived
    | BankEvents.ServiceStarted
    | BankEvents.ServiceFinished
    | BankEvents.CustomerTurnedAway
    | BankEvents.DoorsClosed
)
BankEvents.seal(BankEvent)

# What a process returns: events to schedule, each with its timestep.
type Scheduled = Iterator[tuple[BankEvent, int]]


def minutes(rng: random.Random, mean: float) -> int:
    """An exponentially distributed duration, at least one minute."""
    return max(1, round(rng.expovariate(1 / mean)))


@dataclass
class Arrivals:
    """Each arrival schedules the next one, until the doors close."""

    rng: random.Random
    mean_gap: float
    closed: bool = False

    def __call__(self, event: BankEvent, t: int) -> Scheduled:
        match event:
            case BankEvents.CustomerArrived(customer=c):
                if not self.closed:
                    gap = minutes(self.rng, self.mean_gap)
                    yield BankEvents.CustomerArrived(customer=c + 1), t + gap
            case BankEvents.DoorsClosed():
                self.closed = True
            case (
                BankEvents.ServiceStarted()
                | BankEvents.ServiceFinished()
                | BankEvents.CustomerTurnedAway()
            ):
                pass
            case _:
                assert_never(event)


@dataclass
class Bank:
    """Tellers serve one queue, first come first served.

    A teller is taken when the bank schedules `ServiceStarted`, not when it
    is delivered, so two customers arriving in the same minute can't be given
    the same teller.
    """

    rng: random.Random
    tellers: int
    mean_service: float
    free: list[int] = field(init=False)
    queue: deque[int] = field(default_factory=deque[int])
    doors_open: bool = True

    def __post_init__(self) -> None:
        self.free = list(range(self.tellers))

    def __call__(self, event: BankEvent, t: int) -> Scheduled:
        match event:
            case BankEvents.CustomerArrived(customer=c) if not self.doors_open:
                yield BankEvents.CustomerTurnedAway(customer=c), t
            case BankEvents.CustomerArrived(customer=c):
                if self.free:
                    teller = self.free.pop()
                    yield BankEvents.ServiceStarted(customer=c, teller=teller), t
                else:
                    self.queue.append(c)
            case BankEvents.ServiceStarted(customer=c, teller=teller):
                done = t + minutes(self.rng, self.mean_service)
                yield BankEvents.ServiceFinished(customer=c, teller=teller), done
            case BankEvents.ServiceFinished(teller=teller):
                if self.queue:
                    c = self.queue.popleft()
                    yield BankEvents.ServiceStarted(customer=c, teller=teller), t
                else:
                    self.free.append(teller)
            case BankEvents.DoorsClosed():
                # Customers already inside are still served.
                self.doors_open = False
            case BankEvents.CustomerTurnedAway():
                pass
            case _:
                assert_never(event)


@dataclass
class Stats:
    """Waiting times, from the events alone."""

    arrived_at: dict[int, int] = field(default_factory=dict[int, int])
    waits: list[int] = field(default_factory=list[int])
    turned_away: int = 0
    last_departure: int = 0

    def __call__(self, event: BankEvent, t: int) -> Scheduled:
        match event:
            case BankEvents.CustomerArrived(customer=c):
                self.arrived_at[c] = t
            case BankEvents.ServiceStarted(customer=c):
                self.waits.append(t - self.arrived_at.pop(c))
            case BankEvents.ServiceFinished():
                self.last_departure = t
            case BankEvents.CustomerTurnedAway():
                self.turned_away += 1
            case BankEvents.DoorsClosed():
                pass
            case _:
                assert_never(event)
        yield from ()

    def report(self) -> str:
        served = len(self.waits)
        mean = sum(self.waits) / served if served else 0.0
        return (
            f"served {served}, turned away {self.turned_away}\n"
            f"wait: mean {mean:.1f} min, max {max(self.waits, default=0)} min\n"
            f"last customer left at minute {self.last_departure}"
        )


def describe(event: BankEvent) -> str:
    match event:
        case BankEvents.CustomerArrived(customer=c):
            return f"customer {c} arrives"
        case BankEvents.ServiceStarted(customer=c, teller=teller):
            return f"teller {teller} starts serving customer {c}"
        case BankEvents.ServiceFinished(customer=c, teller=teller):
            return f"teller {teller} finishes with customer {c}"
        case BankEvents.CustomerTurnedAway(customer=c):
            return f"customer {c} is turned away"
        case BankEvents.DoorsClosed():
            return "doors close"
        case _:
            assert_never(event)


@dataclass
class Trace:
    """Prints every event up to minute `until`."""

    until: int

    def __call__(self, event: BankEvent, t: int) -> Scheduled:
        if t <= self.until:
            print(f"{t:>4}  {describe(event)}")
        yield from ()


def simulate(
    seed: int = 1,
    tellers: int = 3,
    mean_gap: float = 2.0,
    mean_service: float = 5.0,
    closes_at: int = 8 * 60,
    trace_until: int = 15,
) -> Stats:
    rng = random.Random(seed)
    stats = Stats()
    loop = EventLoop[BankEvent](
        processes=[
            Arrivals(rng, mean_gap),
            Bank(rng, tellers, mean_service),
            stats,
            Trace(trace_until),
        ]
    )
    loop.add_event(BankEvents.CustomerArrived(customer=0), 0)
    loop.add_event(BankEvents.DoorsClosed(), closes_at)
    loop.run()
    return stats


if __name__ == "__main__":
    print(simulate().report())
