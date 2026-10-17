# superenums

Rust-style enums (sum types / algebraic data types) for Python: variants that carry data and exhaustive matching.

## Status

The core is complete (design in `docs/system-design/`, user guide in `docs/guide.md`). Next come the extensions: serialization (designed in `docs/system-design/`: tag inside the object, extras, a pydantic hook on `Variant`; `superenums.cattrs` and `superenums.pydantic`; msgspec goes through cattrs' msgspec converter, with no module of its own), then Option/Result. An enum is its union alias (`type Shape = Circle | Rect`), and variants are module-level `Variant` subclasses: the module is the namespace. 0.1.0's `Variants` namespace class and `seal` are gone (the design doc records why). In `src/superenums/_core.py`: `Variant`, `SuperEnumError`, and the introspection functions `variants(alias)` and `variant_name`, with the full tooling below.

## Commands

- **Run everything** (before every commit): `uv run scripts/check.py` — pytest (including running the doc examples), the type-level suite (including type-checking the doc examples), pyright + mypy strict on `src/`, `ruff check`, `ruff format --check`. Exits non-zero on any failure.
- Inner loop: `uv run pytest -q`; type-level suite alone: `uv run python tests/typing/run.py`.
- Common commands are also in `Taskfile.yml` (`task check`, `task test`, `task hooks`, ...). If `task` isn't installed, run it with `uvx --from go-task-bin task <name>`.
- **pre-commit**: install once with `uv run pre-commit install`. Hooks (`.pre-commit-config.yaml`) run the file-hygiene checks (pre-commit-hooks), `ruff format`, `ruff check --fix`, actionlint (which also runs shellcheck on workflow `run:` steps), shellcheck on shell scripts, then the full check. The local hooks call `uv run --locked`, so they use the versions pinned in `uv.lock`; after changing dependencies, run `uv lock` or the hooks fail. `uv run pre-commit run --all-files` runs exactly what CI runs.
- **CI** (`.github/workflows/ci.yml`): runs every pre-commit hook on all files for every PR, on Python 3.12, 3.13 and 3.14 (`UV_PYTHON` picks the matrix Python for every `uv` command, including the hooks'; `UV_PYTHON_PREFERENCE: only-managed` makes it uv's latest patch release, not the runner's older system Python). On `main` it runs only when `uv.lock` changes, to refresh the uv cache that PRs restore from.
- **The `main` ruleset** blocks deletion and force-pushes, requires a PR (squash merge only), and requires the status checks `pre-commit (3.12)`, `pre-commit (3.13)` and `pre-commit (3.14)` with the branch up to date. Renaming the CI job or changing the matrix breaks merging until the ruleset is updated to the new names.
- Pin GitHub Actions to exact versions. `astral-sh/setup-uv` doesn't publish floating major tags (`@v10` fails).
- `actionlint-py` ships only a source package, and building it downloads the binary from GitHub. On macOS with python.org Python, that fails with `CERTIFICATE_VERIFY_FAILED` until `Install Certificates.command` has been run. A one-off workaround is `SSL_CERT_FILE=/etc/ssl/cert.pem uv sync`. uv caches the built wheel afterwards.

## Versioning

- Single source: `version` in `pyproject.toml`. Never hard-code it elsewhere. `superenums.__version__` uses `importlib.metadata`.
- Releases happen on merge. `.github/workflows/release.yml` runs on every push to `main`: if `v<version>` isn't tagged yet, it builds, tags and publishes a GitHub Release. On PRs it's a dry run.
- **Feature PRs never change the version.** A release is its own PR that only bumps the version (`task bump -- <part>`, which wraps `uv version --bump`) and releases whatever is on `main`. Never create or push `v*` tags by hand.
- On PRs, the Release workflow fails if the PR changes the version to one that's already tagged. Otherwise that bump would be silently skipped after merge. Its logic is in `.github/scripts/release-check.sh`.
- Hotfixes: fix forward. Merge the fix, then a patch-bump PR, which keeps `main` releasable. Release branches (`release/X.Y` from a tag, with the fix merged to `main` first and then cherry-picked with `git cherry-pick -x`) are the agreed fallback but aren't set up yet. They'd need the release workflow and ruleset extended to `release/**`, plus `--latest=false` and `--notes-start-tag` handling.
- **Releases don't need approval in this project** (the user's call, overriding the global default for now). Merging a PR that changes the version publishes a release. Release whenever `main` has user-facing changes worth shipping, in its own bump PR: patch for fixes, minor for features (pre-1.0), and say which release went out.
- A tag created by the workflow's `GITHUB_TOKEN` doesn't trigger other workflows, so release work belongs in `release.yml` itself.

## Workflow

- Changes go through a branch and a PR, never straight to `main`.
- **A PR whose CI checks all pass may be squash-merged without asking**, version bumps included (see Versioning) (`gh pr merge <n> --squash --delete-branch`), then `git switch main` and `git pull`. Confirm CI is green (`gh pr checks <n> --watch`) first. Don't merge with failing or pending checks.
- The `main` ruleset requires PRs to be up to date. If a PR falls behind after another merge, run `gh pr update-branch <n>` and wait for CI again.

## Tooling

- Use **uv** for everything: environments, dependencies, running tools (`uv run ...`, `uv add --dev ...`). Don't use bare `pip` or globally installed tools.
- **uv itself is pinned** by `[tool.uv] required-version` in `pyproject.toml`. CI's setup-uv reads it, and uv refuses to run locally at any other version. Without the pin, setup-uv installs the latest uv, so CI and releases drift from local. Upgrade deliberately in one PR: `required-version` and the `uv_build` bound in `[build-system]` together, then `uv lock`. Install uv with the standalone installer, so `uv self update <version>` works.
- **ruff** for linting and formatting.
- **pyright, mypy, and ty**, all pinned as dev dependencies. They check the library itself (strict) and run the type-level test suite. ty is pre-1.0: its failures are advisory until it stabilises.
- **pytest** for runtime behaviour.
- **Type-level test suite** (typeshed-style, `tests/typing/cases/`): small `.py` files using `assert_type(...)` for expected narrowing, and ignore comments on lines that must error. Each checker honours only its own comment (mypy `# type: ignore[code]`, pyright `# pyright: ignore[rule]`, ty `# ty: ignore[rule]`), with unused-ignore detection on, so a missing error fails the build. Pyright's `reportUnreachable` is on in the suite, so a complete match's `assert_never` arm carries `# pyright: ignore[reportUnreachable]` as pyright's proof of exhaustiveness. Scheme documented in `tests/typing/run.py`. This suite is how the core promise (checker-proven exhaustiveness) is tested.
- **Doc examples**: every ```` ```python ```` block in `README.md` and `docs/guide.md` (including ones inside a `>` callout) is executed by `tests/test_docs.py`, each as a fresh module registered in `sys.modules` (dataclass resolves quoted annotations through it), so keep each block self-contained. The exception: a block preceded by `<!-- module: name -->` is a module with that name, which later blocks in the same doc can `import` (how the guide shows `shapes.Circle` style). Module names must be unique across the docs. The same test requires every `match` in them to end in `case _: assert_never(subject)`. The guide is ruff-formatted like code; `docs/system-design/` and this file are excluded to keep their compact examples. The type-level suite also type-checks every example (`tests/typing/doc_examples_check.py`) in the configuration the guide recommends: pyright strict + `reportMatchNotExhaustive`, `mypy --strict`, ty. Examples must be clean; an example that deliberately shows wrong code is preceded by an invisible `<!-- expect-type-errors -->` line (inside the `>` callout if it's in one) and must produce errors instead. Extraction is shared in `tests/doc_examples.py`.
- The type-level suite targets Python 3.12 in every checker (pyright, mypy and ty configs in `tests/typing/`), whichever interpreter runs it, so results are identical across the CI matrix.
- Later / lower priority: Hypothesis (property tests).

## Docs

- `docs/guide.md` — the user guide: how to use superenums, with the user-facing traps. Every example is executed by the tests.
- `docs/system-design/` — the design and the reasons for it. The source of truth for settled decisions.
- `examples/` — real-world uses that test the design in anger (`examples/README.md` records what each showed). `bank_tellers.py` is a py-ev queueing simulation: a PEP 723 script pinning py-ev by tag, Python 3.13+, so it's outside `scripts/check.py` and CI. Run with `task example`, type-check with `task example-check`. Editor pyright can't resolve `pyev` there (it's only in the script's uv environment); `task example-check` points the checkers at it.
- `docs/prior-art.md` — survey of existing Python ADT and Option/Result libraries, the stalled `@sealed` PEP, and type-checker exhaustiveness support. Read it before making design decisions.

Keep durable project knowledge (decisions, constraints, traps) in this file or in `docs/`, not in private agent memory.

## Design at a glance

The full design and its rationale are in `docs/system-design/README.md`, which is authoritative. In short:

```python
# shapes.py: the module is the namespace, and holds the behaviour too
class Circle(Variant):
    radius: float  # variants: frozen, slotted dataclasses


class Empty(Variant): ...  # unit variant: Empty() is a cached singleton


type Shape = Circle | Empty  # the alias IS the enum: the only list of variants


def describe(s: Shape) -> str:  # behaviour = free functions with one match
    match s:
        case Circle(radius=r):
            return f"circle {r}"
        case Empty():
            return "empty"
        case _:
            assert_never(s)
```

- Type-checker visibility beats syntax. No plugins; pyright, mypy, and ty must all understand it.
- Python 3.12+, PEP 695 syntax. Generic enums put type parameters on the variants.
- No inheritance between variants. Data shared by every variant goes in a wrapper (composition), not a base class.
- Option/Result and serialization are extensions built on the public API, not the core.

## Known traps to watch

- **pyright config lives in `pyrightconfig.json`, not `pyproject.toml`.** pyright prefers any `pyrightconfig.json` in a parent directory (e.g. one in `~`) over a `[tool.pyright]` section, which can make it scan the whole home directory and run out of memory.
- **ty narrows variants to intersections** (`Rect & ~Circle`) in later `case` arms, because without `@final` a class could inherit from two variants. Exact `assert_type` on the subject fails in ty only; the suite records this with `# ty: ignore[assert-type-unspellable-subtype]`. Exhaustiveness is unaffected.

- **ty and generic variants.** when targeting Python 3.12, ty infers the literal type argument from construction (`trees.Leaf(1)` is `Leaf[Literal[1]]`, not `Leaf[int]`; targeting 3.13+ it infers `Leaf[int]`), and narrows a class pattern on a generic variant to both the subject's specialisation and `Unknown` (`case trees.Leaf(value=v)` gives `v: T | Unknown`). Exact `assert_type`s on these fail in ty only; the suite records them with `# ty: ignore[type-assertion-failure]` (`tests/typing/cases/generics.py`). Mismatched type arguments and exhaustiveness are unaffected.
- **Frozen slotted dataclasses raise a bare `TypeError` for a non-field attribute write** (CPython 3.12: the generated `__setattr__` calls `super(cls, self)` with the pre-slots class). `typing`'s subscripted call (`Leaf[int](1)`) sets `__orig_class__` on the new value and tolerates only `AttributeError`, so `_VariantMeta` replaces each variant's `__setattr__`/`__delattr__` with one that always raises `FrozenInstanceError`.
- **`variants()` reads variant classes, not type arguments.** `_alias_members` unwraps each alias member with `typing.get_origin`, so `Leaf[T]` and `Leaf[int]` both count as `Leaf`. Nothing evaluates variant annotations at class creation, which is what lets recursive variants use quoted annotations naming an alias defined after them.
- **`dataclass(slots=True)` returns a new class.** Variants are made slotted dataclasses in a metaclass (`_VariantMeta.__new__`), before the class is bound to its name, so each variant is one class object. Doing it in `__init_subclass__` would leave the class body's name bound to the unslotted original. dataclass rebuilds the slotted class through the same metaclass; the rebuild is recognised by a private marker attribute (`_BUILDING`) that superenums sets before calling `dataclass` and removes after, never by `__slots__` presence (a user's own `__slots__` is rejected). The same marker lets `_VariantMeta.__setattr__` tell superenums' own `dataclass` call from a user's `@dataclass` over a finished variant, which it refuses when `dataclass` first sets `__dataclass_params__`.
- **Unit variants are cached when the class is created** (`_VariantMeta.__new__`), which gives each variant with no fields a `__new__` returning its one instance and a `__reduce__` that rebuilds by calling the class. `__new__` alone is not enough: pickle protocols 0 and 1 rebuild through `copyreg._reconstructor`, which calls `object.__new__` directly and would make a second instance.
- **Annotating with a class instead of the alias** (a shared base class, or a plain class grouping the variants) silently defeats exhaustiveness. The guide steers away from both (one module per enum; shared data in a wrapper).
- **Unit variant pattern without parentheses**: `case shapes.Empty:` (dotted) is a value pattern that never matches; checkers catch it as a non-exhaustive match, unchecked code fails silently. A bare `case Empty:` is a capture pattern, which Python rejects unless it is the last arm.
- **mypy doesn't narrow a tuple of unions**, so `match (state, event):` is never exhaustive in mypy (pyright and ty prove it). Pinned in `tests/typing/cases/several_enums.py`; the guide shows nested matches.

- **Recursive generic enums need Python 3.12.4+ wherever annotations are evaluated** (e.g. cattrs): before it, `typing.get_type_hints` can't see a class's PEP 695 type parameters, so `"Tree[T]"` raises `NameError`. The local python.org 3.12.2 hits it, and so would the runner's system 3.12.3; the test skips there, and CI uses uv's managed Python to run it.
- **Serialization extensions are optional dependencies.** Each lives in its own module (`superenums/cattrs.py`), needs its extra in `[project.optional-dependencies]` and a pinned dev dependency, and nothing else may import its library: `tests/test_optional_dependencies.py` imports the core with them blocked.
- **pydantic support is installed lazily by `_VariantMeta.__pydantic_config__`**, a property pydantic reads from every dataclass (generic ones included) before collecting its decorators. It installs the tag decorators on `Variant` (`superenums.pydantic.prepare`), returns the variant's own config, and raises `AttributeError` when there is none (pydantic < 2.14 needs that). `__get_pydantic_core_schema__` was rejected: pydantic never calls it for `Leaf[int]`. Each pydantic test that depends on the install happening on first contact runs in a subprocess, since any earlier test installs it.
- **Testing an extension against other library versions:** `uv run --isolated --with <lib>==<v> --with-editable . pytest ...`. With `--with .` uv reuses its cached build of the same superenums version, so the tests run against stale source.
- **`Variant` declares `__dataclass_fields__` for checkers only** (under `TYPE_CHECKING`), so `dataclasses.fields(cls)` type-checks for the classes `variants()` returns.

## Open questions

- A `?`-like early return (e.g. generator do-notation). Belongs with the Result extension.
