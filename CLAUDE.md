# superenums

Rust-style enums (sum types / algebraic data types) for Python: variants that carry data and exhaustive matching.

## Status

Core design settled (see `docs/system-design/`). In `src/superenums/_core.py`: `Variant`, `Variants`, `SuperEnumError`, and `seal` (verifies the alias, locks the namespace, enables construction), with the full tooling below.

## Commands

- **Run everything** (before every commit): `uv run scripts/check.py` — pytest (including the README examples), the type-level suite, pyright + mypy strict on `src/`, `ruff check`, `ruff format --check`. Exits non-zero on any failure.
- Inner loop: `uv run pytest -q`; type-level suite alone: `uv run python tests/typing/run.py`.

## Tooling

- Use **uv** for everything: environments, dependencies, running tools (`uv run ...`, `uv add --dev ...`). Don't use bare `pip` or globally installed tools.
- **ruff** for linting and formatting.
- **pyright, mypy, and ty**, all pinned as dev dependencies. They check the library itself (strict) and run the type-level test suite. ty is pre-1.0: its failures are advisory until it stabilises.
- **pytest** for runtime behaviour.
- **Type-level test suite** (typeshed-style, `tests/typing/cases/`): small `.py` files using `assert_type(...)` for expected narrowing, and ignore comments on lines that must error. Each checker honours only its own comment (mypy `# type: ignore[code]`, pyright `# pyright: ignore[rule]`, ty `# ty: ignore[rule]`), with unused-ignore detection on, so a missing error fails the build. Pyright's `reportUnreachable` is on in the suite, so a complete match's `assert_never` arm carries `# pyright: ignore[reportUnreachable]` as pyright's proof of exhaustiveness. Scheme documented in `tests/typing/run.py`. This suite is how the core promise (checker-proven exhaustiveness) is tested.
- **README examples** (```` ```python ```` blocks) are executed by `tests/test_readme.py`; keep each block self-contained.
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

- **pyright config lives in `pyrightconfig.json`, not `pyproject.toml`.** pyright prefers any `pyrightconfig.json` in a parent directory (e.g. one in `~`) over a `[tool.pyright]` section, which can make it scan the whole home directory and run out of memory.
- **ty narrows variants to intersections** (`Rect & ~Circle`) in later `case` arms, because without `@final` a class could inherit from two variants. Exact `assert_type` on the subject fails in ty only; the suite records this with `# ty: ignore[assert-type-unspellable-subtype]`. Exhaustiveness is unaffected.

- **`dataclass(slots=True)` returns a new class.** Variants are made slotted dataclasses in a metaclass (`_VariantMeta.__new__`), before the class is bound in the namespace body, so each variant is one class object. Doing it in `__init_subclass__` would leave the namespace body, the collected variants, and `seal` holding the unslotted original.
- **The unsealed-construction guard is a stand-in `__init__`**, swapped back to the dataclass `__init__` by `seal`, so sealed construction has no overhead. Don't guard via `__new__`: deleting a `__new__` from a class leaves CPython's `slot_tp_new` in place, and `object.__new__` then rejects constructor arguments.
- **Annotating with the namespace class** (`s: Shapes` instead of the union alias `s: Shape`) silently defeats exhaustiveness. It is currently only discouraged. Watch how often it bites during development, and consider stronger prevention (see `docs/system-design/README.md`).
- **Unit variant pattern without parentheses** (`case Shapes.Empty:` instead of `case Shapes.Empty():`) never matches. Checkers catch it as a non-exhaustive match; unchecked code fails silently.

## Open questions

- A `?`-like early return (e.g. generator do-notation). Belongs with the Result extension.
