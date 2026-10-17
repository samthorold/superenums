# Prior art: Rust-style enums in Python

Survey date: 2026-10-17. Re-check maintenance status before relying on it.

Existing work falls into four camps. None of them combines declaration ergonomics, sealing, exhaustiveness, and type-checker support.

## 1. ADT / sum-type libraries (the core feature)

| Library | Declaration style | Exhaustiveness | Type-checker story | Status |
|---|---|---|---|---|
| [`adt`](https://github.com/jspahrsummers/adt) | `@adt` class with `LEFT: Case[int]` annotations | Runtime: `.match(left=..., right=...)` raises if a case is missing | Needs a custom mypy plugin; no pyright support | Archived Oct 2024, "experimental" |
| [`sumtypes`](https://github.com/radix/sumtypes) | `@sumtype` + `constructor('x', 'y')`, built on attrs | Runtime: `@match(T)` class with one method per case; `match_partial` for subsets | None (fields are untyped strings) | Small and quiet; predates type hints |
| [Expression `@tagged_union`](https://expression.readthedocs.io/en/latest/tutorial/data_modelling.html) | Dataclass with `tag: Literal[...]` + one `case()` field per variant | Not covered | Pyright-strict friendly, but every case is the same class, so no per-variant narrowing | Active |
| [PySumTypes](https://pypi.org/project/PySumTypes), [algebraic-data-types](https://pypi.org/project/algebraic-data-types/0.1.1), [tagged-union](https://tagged-union.readthedocs.io/) | Various decorators over dataclasses | Varies | Little or none | Niche |

Lessons:

- Each picks one of two designs: runtime magic that needs a type-checker plugin (`adt`), or checker-friendly but with variants collapsed into one type (Expression).
- A mypy-only plugin is a dead end. It excludes pyright/Pylance and `ty`.
- A runtime `.match(**handlers)` that checks completeness is the established way to get exhaustiveness without a type checker. Worth keeping.

## 2. Option / Result libraries

| Library | What it offers | Notes |
|---|---|---|
| [`returns` (dry-python)](https://github.com/dry-python/returns) | `Maybe`, `Result`, `IO`, `Future`, `RequiresContext`; `@safe`, `flow`, `bind`, do-notation | Most complete, active. Haskell-flavoured; requires a mypy plugin. Reported false positive on exhaustive `match` due to lack of `@sealed` |
| [`result` (rustedpy)](https://github.com/rustedpy/result) + [`maybe`](https://github.com/rustedpy/maybe) | `Ok`/`Err` with Rust method names, `match` support, generator-based `do()`, `@as_result` decorator | Closest to Rust; fully typed with no plugin because `Result = Ok[T] \| Err[E]` is a plain union. Archived June 2026, unmaintained |
| [Expression](https://github.com/dbrattli/Expression) | `Option`, `Result`, `pipe`, `@effect.result` generator do-notation | F#-flavoured, active, pyright-strict |
| [`rusty-results`](https://pypi.org/project/rusty-results), [`reop`](https://pypi.org/project/reop/), [`rustypie`](https://pypi.org/p/rustypie) | Rust-like `Option`/`Result` | Small clones |

Lessons:

- rustedpy's plain union of two small generic classes is the design type checkers handle best: `match` narrows correctly with no plugin.
- Generator do-notation (`yield` / `yield from` short-circuiting) is how Python libraries approximate `?`. Both rustedpy and Expression use it.
- With rustedpy archived, there is an open niche for a maintained, Rust-flavoured, plugin-free `Option`/`Result`.

## 3. Language and typing-spec efforts (the "sealed" problem)

- [Draft PEP: `@sealed` decorator](https://discuss.python.org/t/draft-pep-sealed-decorator-for-static-typing/49206) (March 2024, aimed at 3.13). A sealed base would act as a union of its direct subclasses in the same module, enabling exhaustive `match`. No runtime effect. Described as "stranded" in an [Aug 2026 thread](https://discuss.python.org/t/typing-feature-to-statically-get-all-subclasses-of-class/108671).
- Earlier [typing-sig `Sealed` base-class idea](https://mail.python.org/archives/list/typing-sig@python.org/thread/QSCT2N4RFPRQN2U7NIX6VCNVNDHGO22U/), including a runtime check. Stalled on whether "sealed" should imply "abstract".
- [LiteralEnum proposal](https://discuss.python.org/t/proposal-literalenum-runtime-literals-with-static-exhaustiveness/106000/15): runtime values with static exhaustiveness.
- Community workarounds:
  - keep an explicit union alias and assert in tests/CI that `Base.__subclasses__()` matches it;
  - use `__init_subclass__` to block outside subclassing at runtime.

## 4. Type checkers today

- Pyright: [`reportMatchNotExhaustive`](https://github.com/microsoft/pyright/blob/main/docs/configuration.md) catches non-exhaustive `match` over unions, enums, and literals. Off by default; an error only in `strict` mode.
- ty (Astral): has [match exhaustiveness and reachability checking](https://git.joshthomas.dev/mirrors/ruff/src/commit/2a00eca66b17de90498445996712149a8fc0e3bb/crates/ty_python_semantic/resources/mdtest).
- mypy: narrows in `match` and supports the `assert_never()` idiom.
- All three work without plugins only when the type is a real `A | B | C` union of real classes.

## Adjacent: serialization-focused tagged unions

Pydantic discriminated unions, msgspec tagged unions, and [cattrs' tagged-union strategy](https://catt.rs/en/stable/strategies.html) handle storing and loading a union with a tag field. They are not Rust enums, but superenums should interoperate with them rather than compete.

## Implications for superenums

1. **No plugins.** Every plugin-dependent library is dead or tied to mypy. The design must be visible to pyright, mypy, and ty out of the box: variants are real classes, and the enum type can be expressed as a real union.
2. **The unfilled gap:** Rust-like ergonomics (namespaced `Shape.Circle(r=1.0)`, methods on the enum, sealing, immutability) plus plugin-free static exhaustiveness plus a runtime fallback (`.match(**handlers)`, sealing via `__init_subclass__`).
3. **Option/Result is a free win.** rustedpy's well-understood API has no maintained home. Built on our own enum core, it also exercises generic variants.
4. **Key technical risk:** getting `class Shape(SuperEnum)` with nested variant classes to be treated as `Circle | Rect | Empty` by checkers without `@sealed`. Options include exporting an explicit alias (`type ShapeT = Shape.Circle | Shape.Rect`) or `dataclass_transform` tricks. Prototype this first.

## Other sources

- [sumtypes docs](https://sumtypes.readthedocs.io)
- [Expression tagged-union reference](https://expression.readthedocs.io/en/latest/reference/union.html)
- [Result-in-stdlib discussion](https://discuss.python.org/t/introduce-result-class-to-allow-a-modern-representation-of-failure-cases/67174/2)
- [Preferred Networks: exhaustive union match in Python](https://www.preferred.jp/en/blog/tech/python-exhaustive-union-match)
