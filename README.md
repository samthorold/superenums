# superenums

Rust-style enums for Python: variants that carry data, and `match` statements your type checker proves exhaustive.

pyright, mypy, and ty all understand superenums with no plugin. Requires Python 3.12+.

## Quickstart

```python
from typing import assert_never

from superenums import Variant, Variants


class Shapes(Variants):  # the namespace holds the variants
    class Circle(Variant):
        radius: float

    class Rect(Variant):
        w: float
        h: float

    class Empty(Variant): ...  # a unit variant: no fields


type Shape = Shapes.Circle | Shapes.Rect | Shapes.Empty  # the enum
Shapes.seal(Shape)  # checks the alias lists every variant


def area(s: Shape) -> float:  # annotate with the enum, not the namespace
    match s:
        case Shapes.Circle(radius=r):
            return 3.14159 * r * r
        case Shapes.Rect(w, h):
            return w * h
        case Shapes.Empty():
            return 0.0
        case _:
            assert_never(s)


assert area(Shapes.Circle(radius=1.0)) == 3.14159
assert area(Shapes.Rect(2.0, 3.0)) == 6.0
assert area(Shapes.Empty()) == 0.0
```

An enum has two names. `Shapes` is the **namespace** that holds the variants, so you write `Shapes.Circle(radius=1.0)`. `Shape` is the **enum**: the union alias you use in annotations. A type checker can prove a `match` exhaustive only over a union, so annotate with `Shape`, never `Shapes`.

`Shapes.seal(Shape)` connects the two. Write it right after the alias.

Variants are dataclasses: build them positionally or by keyword, and match them with positional or keyword class patterns, in field order. Unit variants still need parentheses, both to construct (`Shapes.Empty()`) and to match (`case Shapes.Empty():`).

Variant values are immutable and compare by variant and field values, so they work in sets and as dict keys. A changed value is a new value:

```python
import dataclasses

from superenums import Variant, Variants


class Shapes(Variants):
    class Circle(Variant):
        radius: float

    class Square(Variant):
        side: float


type Shape = Shapes.Circle | Shapes.Square
Shapes.seal(Shape)

circle = Shapes.Circle(radius=1.0)
assert dataclasses.replace(circle, radius=2.0) == Shapes.Circle(radius=2.0)
# different variants never compare equal, even with identical fields
assert len({Shapes.Circle(1.0), Shapes.Square(1.0)}) == 2
assert repr(circle) == "Shapes.Circle(radius=1.0)"
```

End every `match` over an enum with `case _: assert_never(s)`. If a variant is missing, pyright, mypy, and ty each report an error on that line, whatever the function returns. At runtime, a value that gets through anyway raises an `AssertionError`.

## Learn more

The [guide](docs/guide.md) covers the rest: generic and recursive enums, unit variants, the traps to avoid, when to use a stdlib enum instead, introspection, and type-checker setup.

## Development

Tooling is managed with [uv](https://docs.astral.sh/uv/). Common commands are in `Taskfile.yml`, run with [Task](https://taskfile.dev) (`brew install go-task`):

```sh
uv sync                     # create .venv with dev tools
uv run pre-commit install   # install git hooks
task                        # list tasks
task check                  # run every check (also: uv run scripts/check.py)
task test                   # uv run pytest (extra args: task test -- -k name)
task hooks                  # every pre-commit hook on all files, as CI runs them
```

See [CLAUDE.md](CLAUDE.md) for what the checks cover.

## Releasing

The version lives in `pyproject.toml` only; `superenums.__version__` reads it
from the installed package metadata.

Feature PRs don't change the version. To release, open a PR that only bumps it
(`task bump -- patch|minor|major`) and merge it. The Release workflow then tags
`vX.Y.Z` and publishes a GitHub Release with the built distributions and
generated notes. On PRs, the workflow's summary says whether merging will
publish a release.
