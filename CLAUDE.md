# superenums

Rust-style enums (sum types / algebraic data types) for Python: variants that carry data and exhaustive matching.

## Status

The core is complete (design in `docs/system-design/`, user guide in `docs/guide.md`). Next come the extensions (Option/Result, serialization). In `src/superenums/_core.py`: `Variant`, `Variants`, `SuperEnumError`, `seal` (verifies the alias, locks the namespace, enables construction), and the introspection functions `variants`, `alias`, `namespace_of`, `variant_name` (module-level, so variant names never shadow them; a namespace binding `seal` is rejected for the same reason), with the full tooling below.

## Commands

- **Run everything** (before every commit): `uv run scripts/check.py` — pytest (including running the doc examples), the type-level suite (including type-checking the doc examples), pyright + mypy strict on `src/`, `ruff check`, `ruff format --check`. Exits non-zero on any failure.
- Inner loop: `uv run pytest -q`; type-level suite alone: `uv run python tests/typing/run.py`.
- Common commands are also in `Taskfile.yml` (`task check`, `task test`, `task hooks`, ...). If `task` isn't installed, run it with `uvx --from go-task-bin task <name>`.
- **pre-commit**: install once with `uv run pre-commit install`. Hooks (`.pre-commit-config.yaml`) run the file-hygiene checks (pre-commit-hooks), `ruff format`, `ruff check --fix`, actionlint (which also runs shellcheck on workflow `run:` steps), shellcheck on shell scripts, then the full check. The local hooks call `uv run --locked`, so they use the versions pinned in `uv.lock`; after changing dependencies, run `uv lock` or the hooks fail. `uv run pre-commit run --all-files` runs exactly what CI runs.
- **CI** (`.github/workflows/ci.yml`): runs every pre-commit hook on all files for every PR, on Python 3.12, 3.13 and 3.14 (`UV_PYTHON` picks the matrix Python for every `uv` command, including the hooks'). On `main` it runs only when `uv.lock` changes, to refresh the uv cache that PRs restore from.
- **The `main` ruleset** blocks deletion and force-pushes, requires a PR (squash merge only), and requires the status checks `pre-commit (3.12)`, `pre-commit (3.13)` and `pre-commit (3.14)` with the branch up to date. Renaming the CI job or changing the matrix breaks merging until the ruleset is updated to the new names.
- Pin GitHub Actions to exact versions. `astral-sh/setup-uv` doesn't publish floating major tags (`@v10` fails).
- `actionlint-py` ships only a source package, and building it downloads the binary from GitHub. On macOS with python.org Python, that fails with `CERTIFICATE_VERIFY_FAILED` until `Install Certificates.command` has been run. A one-off workaround is `SSL_CERT_FILE=/etc/ssl/cert.pem uv sync`. uv caches the built wheel afterwards.

## Workflow

- Changes go through a branch and a PR, never straight to `main`.
- **A PR whose CI checks all pass may be squash-merged without asking** (`gh pr merge <n> --squash --delete-branch`), then `git switch main` and `git pull`. Confirm CI is green (`gh pr checks <n> --watch`) first. Don't merge with failing or pending checks.
- The `main` ruleset requires PRs to be up to date. If a PR falls behind after another merge, run `gh pr update-branch <n>` and wait for CI again.

## Tooling

- Use **uv** for everything: environments, dependencies, running tools (`uv run ...`, `uv add --dev ...`). Don't use bare `pip` or globally installed tools.
- **ruff** for linting and formatting.
- **pyright, mypy, and ty**, all pinned as dev dependencies. They check the library itself (strict) and run the type-level test suite. ty is pre-1.0: its failures are advisory until it stabilises.
- **pytest** for runtime behaviour.
- **Type-level test suite** (typeshed-style, `tests/typing/cases/`): small `.py` files using `assert_type(...)` for expected narrowing, and ignore comments on lines that must error. Each checker honours only its own comment (mypy `# type: ignore[code]`, pyright `# pyright: ignore[rule]`, ty `# ty: ignore[rule]`), with unused-ignore detection on, so a missing error fails the build. Pyright's `reportUnreachable` is on in the suite, so a complete match's `assert_never` arm carries `# pyright: ignore[reportUnreachable]` as pyright's proof of exhaustiveness. Scheme documented in `tests/typing/run.py`. This suite is how the core promise (checker-proven exhaustiveness) is tested.
- **Doc examples**: every ```` ```python ```` block in `README.md` and `docs/guide.md` (including ones inside a `>` callout) is executed by `tests/test_docs.py`, each as a fresh module registered in `sys.modules` (dataclass resolves quoted annotations through it), so keep each block self-contained. The same test requires every `match` in them to end in `case _: assert_never(subject)`. The guide is ruff-formatted like code; `docs/system-design/` and this file are excluded to keep their compact examples. The type-level suite also type-checks every example (`tests/typing/doc_examples_check.py`) in the configuration the guide recommends: pyright strict + `reportMatchNotExhaustive`, `mypy --strict`, ty. Examples must be clean; an example that deliberately shows wrong code is preceded by an invisible `<!-- expect-type-errors -->` line (inside the `>` callout if it's in one) and must produce errors instead. Extraction is shared in `tests/doc_examples.py`.
- The type-level suite targets Python 3.12 in every checker (pyright, mypy and ty configs in `tests/typing/`), whichever interpreter runs it, so results are identical across the CI matrix.
- Later / lower priority: Hypothesis (property tests).

## Docs

- `docs/guide.md` — the user guide: how to use superenums, with the user-facing traps. Every example is executed by the tests.
- `docs/system-design/` — the design and the reasons for it. The source of truth for settled decisions.
- `docs/prior-art.md` — survey of existing Python ADT and Option/Result libraries, the stalled `@sealed` PEP, and type-checker exhaustiveness support. Read it before making design decisions.

Keep durable project knowledge (decisions, constraints, traps) in this file or in `docs/`, not in private agent memory.

## Design at a glance

The full design and its rationale are in `docs/system-design/README.md`, which is authoritative. In short:

```python
class Shapes(Variants):  # namespace (plural)
    class Circle(Variant):
        radius: float  # variants: frozen, slotted dataclasses

    class Empty(Variant): ...  # unit variant: Shapes.Empty() is a cached singleton


type Shape = Shapes.Circle | Shapes.Empty  # the enum (singular): annotate with this
Shapes.seal(Shape)  # checks alias == variants, locks namespace


def describe(s: Shape) -> str:  # behaviour = free functions with one match
    match s:
        case Shapes.Circle(radius=r):
            return f"circle {r}"
        case Shapes.Empty():
            return "empty"
        case _:
            assert_never(s)
```

- Type-checker visibility beats syntax. No plugins; pyright, mypy, and ty must all understand it.
- Python 3.12+, PEP 695 syntax. Generic enums put type parameters on variants, never on the namespace.
- Option/Result and serialization are extensions built on the public API, not the core.

## Known traps to watch

- **pyright config lives in `pyrightconfig.json`, not `pyproject.toml`.** pyright prefers any `pyrightconfig.json` in a parent directory (e.g. one in `~`) over a `[tool.pyright]` section, which can make it scan the whole home directory and run out of memory.
- **ty narrows variants to intersections** (`Rect & ~Circle`) in later `case` arms, because without `@final` a class could inherit from two variants. Exact `assert_type` on the subject fails in ty only; the suite records this with `# ty: ignore[assert-type-unspellable-subtype]`. Exhaustiveness is unaffected.

- **ty and generic variants.** when targeting Python 3.12, ty infers the literal type argument from construction (`Trees.Leaf(1)` is `Leaf[Literal[1]]`, not `Leaf[int]`; targeting 3.13+ it infers `Leaf[int]`), and narrows a class pattern on a generic variant to both the subject's specialisation and `Unknown` (`case Trees.Leaf(value=v)` gives `v: T | Unknown`). Exact `assert_type`s on these fail in ty only; the suite records them with `# ty: ignore[type-assertion-failure]` (`tests/typing/cases/generics.py`). Mismatched type arguments and exhaustiveness are unaffected.
- **Frozen slotted dataclasses raise a bare `TypeError` for a non-field attribute write** (CPython 3.12: the generated `__setattr__` calls `super(cls, self)` with the pre-slots class). `typing`'s subscripted call (`Trees.Leaf[int](1)`) sets `__orig_class__` on the new value and tolerates only `AttributeError`, so `_VariantMeta` replaces each variant's `__setattr__`/`__delattr__` with one that always raises `FrozenInstanceError`.
- **Seal compares variant classes, not type arguments.** `_alias_variants` unwraps each alias member with `typing.get_origin`, so `Trees.Leaf[T]` and `Trees.Leaf[int]` both count as `Trees.Leaf`. Nothing evaluates variant annotations at class creation, which is what lets recursive variants use quoted annotations naming a module-level alias defined after the namespace.
- **`dataclass(slots=True)` returns a new class.** Variants are made slotted dataclasses in a metaclass (`_VariantMeta.__new__`), before the class is bound in the namespace body, so each variant is one class object. Doing it in `__init_subclass__` would leave the namespace body, the collected variants, and `seal` holding the unslotted original. dataclass rebuilds the slotted class through the same metaclass; the rebuild is recognised by a private marker attribute (`_BUILDING`) that superenums sets before calling `dataclass` and removes after, never by `__slots__` presence (a user's own `__slots__` is rejected). The same marker lets `_VariantMeta.__setattr__` tell superenums' own `dataclass` call from a user's `@dataclass` over a finished variant, which it refuses when `dataclass` first sets `__dataclass_params__`.
- **The unsealed-construction guard is a stand-in `__init__`**, swapped back to the dataclass `__init__` by `seal`, so sealed construction has no overhead. Don't guard via `__new__`: deleting a `__new__` from a class leaves CPython's `slot_tp_new` in place, and `object.__new__` then rejects constructor arguments.
- **Unit variants are cached by `seal`**, which gives each variant with no fields a `__new__` returning its one instance and a `__reduce__` that rebuilds by calling the class. `__new__` alone is not enough: pickle protocols 0 and 1 rebuild through `copyreg._reconstructor`, which calls `object.__new__` directly and would make a second instance.
- **Annotating with the namespace class** (`s: Shapes` instead of the union alias `s: Shape`) silently defeats exhaustiveness. It is currently only discouraged (a callout in the guide; pinned per checker in `tests/typing/cases/namespace_annotation.py`). Watch how often it bites during development, and consider stronger prevention (see `docs/system-design/README.md`).
- **Unit variant pattern without parentheses** (`case Shapes.Empty:` instead of `case Shapes.Empty():`) never matches. Checkers catch it as a non-exhaustive match; unchecked code fails silently.

## Open questions

- A `?`-like early return (e.g. generator do-notation). Belongs with the Result extension.
