# Examples

Real-world uses of superenums, to test the design against code it wasn't written for.

## Bank tellers (`bank_tellers.py`)

A queueing simulation built on [py-ev](https://github.com/samthorold/py-ev), a discrete event loop. Customers arrive at random, wait in one queue for one of three tellers, and are turned away after the doors close. py-ev is generic in its event data (`EventLoop[T]`, `QueueItem[T]`); here `T` is one enum, `BankEvent`, with five variants (four with fields, one unit variant).

```sh
task example        # uv run examples/bank_tellers.py
task example-check  # pyright strict + reportMatchNotExhaustive, mypy --strict, ty
```

The script declares its own dependencies (PEP 723): py-ev pinned to a tag, and this checkout of superenums. py-ev needs Python 3.13+, so the example isn't part of `scripts/check.py` or CI, which also run 3.12.

### What it shows

- **py-ev takes the enum as `T` unchanged.** `EventLoop[BankEvent]` works at runtime and in all three checkers. Neither library needs to know about the other.
- **Broadcasting makes exhaustiveness pay.** py-ev delivers every event to every process, so each process is one `match` over the whole enum. Adding a variant (tried: `TellerOnBreak(teller: int)`) fails all four matches (`Arrivals`, `Bank`, `Stats`, `describe`) in pyright, mypy and ty, before anything runs. Each process then has to decide what the new event means to it.
- **The cost is ignore arms.** A process lists the variants it doesn't care about (`case A() | B(): pass`). That's the point, but it's noisy, and `case _: pass` would silence the checker. Nothing stops someone writing that.
- **Guards work.** `case CustomerArrived(customer=c) if not self.doors_open:` followed by an unguarded `case CustomerArrived(...)`: all three checkers still prove the match exhaustive.
- **Generator processes are a good fit.** `yield event, t` from a `match` arm reads well. A process that never schedules anything needs `yield from ()` to stay a generator.
