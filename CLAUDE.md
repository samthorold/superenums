# superenums

Rust-style enums (sum types / algebraic data types) for Python: variants that carry data, exhaustive matching, and methods on the enum.

## Status

Early design. No code yet. See `docs/` for research.

## Docs

- `docs/prior-art.md` — survey of existing Python ADT and Option/Result libraries, the stalled `@sealed` PEP, and type-checker exhaustiveness support. Read it before making design decisions.

Keep durable project knowledge (decisions, constraints, traps) in this file or in `docs/`, not in private agent memory.

## Working design direction (not yet final)

- **No type-checker plugins.** Pyright, mypy, and ty must understand the library out of the box. In practice: variants are real classes, and an enum type can be expressed as a real `A | B | C` union.
- **Exhaustiveness at both levels:** static via the type checker's `match` checks, plus a runtime fallback such as a `.match(**handlers)` method that rejects missing cases.
- **Sealed at runtime:** block subclassing from outside the enum declaration (e.g. `__init_subclass__`).
- **Option / Result** built on the core, as a test of generic variants.

## Open questions

- Python version floor (3.12+ would allow `type` aliases and the new generic syntax).
- Declaration syntax: nested variant classes vs. a terser form. First prototype: confirm pyright flags a non-exhaustive `match` on the chosen form.
- Whether to include a `?`-like early return (e.g. generator do-notation).
