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
- **Ignore arms are a per-process choice.** Every process gets every event, so each one says what to do with the events it doesn't care about. Listing them (`case A() | B(): pass`) means a new variant fails that process until someone decides what it means there. `Bank` and `Stats` need that, because a new event like `TellerOnBreak` can change their answers. `case _: pass` lets new variants fall through without a report, which suits a filter like `Trace` that is correct whatever the variants are. In DES code the wildcard form will be common, and that's fine: it's visible, and it's chosen per process. The guide's [Handling only some variants](../docs/guide.md#handling-only-some-variants) section describes both forms.
- **Guards work.** `case CustomerArrived(customer=c) if not self.doors_open:` followed by an unguarded `case CustomerArrived(...)`: all three checkers still prove the match exhaustive.
- **Same-typed fields are a swap risk.** `ServiceStarted(customer, teller)` takes two ints, so `ServiceStarted(teller, customer)` type-checks too. The example marks those variants `_: KW_ONLY`, so every checker rejects positional arguments and patterns for them (see the guide's [Keyword-only fields](../docs/guide.md#keyword-only-fields)).
- **Generator processes are a good fit.** `yield event, t` from a `match` arm reads well. A process that never schedules anything needs `yield from ()` to stay a generator.
