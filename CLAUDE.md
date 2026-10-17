# superenums

Rust-style enums (sum types / algebraic data types) for Python: variants that carry data and exhaustive matching.

## Status

Core design settled (see `docs/system-design/`). No code yet.

## Tooling

- Use **uv** for everything: environments, dependencies, running tools (`uv run ...`, `uv add --dev ...`). Don't use bare `pip` or globally installed tools.
- **ruff** for linting and formatting.
- **pyright, mypy, and ty**, all pinned as dev dependencies. They check the library itself (strict) and run the type-level test suite. ty is pre-1.0: its failures are advisory until it stabilises.
- **pytest** for runtime behaviour.
- **Type-level test suite** (typeshed-style): small `.py` files using `assert_type(...)` for expected narrowing, and `# type: ignore[...]` / `# pyright: ignore[...]` on lines that must error. Run each checker with unused-ignore warnings on, so a missing error fails the build. This suite is how the core promise (checker-proven exhaustiveness) is tested.
- Later / lower priority: Hypothesis (property tests), pre-commit or prek, a GitHub Actions matrix (Python 3.12–3.14 × three checkers).

## Docs

- `docs/system-design/` — the design and the reasons for it. The source of truth for settled decisions.
- `docs/prior-art.md` — survey of existing Python ADT and Option/Result libraries, the stalled `@sealed` PEP, and type-checker exhaustiveness support. Read it before making design decisions.

Keep durable project knowledge (decisions, constraints, traps) in this file or in `docs/`, not in private agent memory.

## Design at a glance

The full design and its rationale are in `docs/system-design/README.md`, which is authoritative. In short:

```python
class Shapes(Variants):                      # namespace (plural)
    class Circle(Variant): radius: float     # variants: frozen, slotted dataclasses
    class Empty(Variant): ...                # unit variant: Shapes.Empty() is a cached singleton

type Shape = Shapes.Circle | Shapes.Empty    # the enum (singular): annotate with this
Shapes.seal(Shape)                           # checks alias == variants, locks namespace

def describe(s: Shape) -> str:               # behaviour = free functions with one match
    match s:
        case Shapes.Circle(radius=r): return f"circle {r}"
        case Shapes.Empty(): return "empty"
        case _: assert_never(s)
```

- Type-checker visibility beats syntax. No plugins; pyright, mypy, and ty must all understand it.
- Python 3.12+, PEP 695 syntax. Generic enums put type parameters on variants, never on the namespace.
- Option/Result and serialization are extensions built on the public API, not the core.

## Known traps to watch

- **Annotating with the namespace class** (`s: Shapes` instead of the union alias `s: Shape`) silently defeats exhaustiveness. It is currently only discouraged. Watch how often it bites during development, and consider stronger prevention (see `docs/system-design/README.md`).
- **Unit variant pattern without parentheses** (`case Shapes.Empty:` instead of `case Shapes.Empty():`) never matches. Checkers catch it as a non-exhaustive match; unchecked code fails silently.

## Open questions

- A `?`-like early return (e.g. generator do-notation). Belongs with the Result extension.
