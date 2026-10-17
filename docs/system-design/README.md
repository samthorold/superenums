# superenums system design

superenums brings Rust-style enums (sum types whose variants carry data) to Python. It is a production library for typed codebases.

> This document describes the design from 0.2.0 on: the enum is its union alias, and variants live at module level. 0.1.0 had an earlier design with a namespace class and `seal`. Why the namespace was dropped is recorded under [Rejected: a namespace class](#rejected-a-namespace-class).

## Core promise

Illegal states are unrepresentable, and the user's type checker proves that a `match` over an enum is exhaustive.

Static proof is what matters here. Runtime checks find a missing case only when that code path runs. A type checker finds it everywhere, including the moment a new variant is added. That is what makes Rust enums safe to change, and it is the property no maintained Python library offers today without a plugin (see [prior art](../prior-art.md)).

## What superenums adds, and what it doesn't

Most of a Rust enum's power doesn't come from the enum feature. It comes from three things: modelling with one closed type instead of a struct whose fields can contradict each other; a compiler that refuses an incomplete `match`; and an ecosystem that uses sum types by default (`Option`, `Result`).

Python's type system already has the first. A union of frozen dataclasses is a closed type, a `match` over it can be proven exhaustive, and a checker refuses to read a field before the value is narrowed to its variant. superenums cannot add type-system power, and doesn't try. What it adds:

- **one uniform declaration**: subclassing `Variant` makes a frozen, slotted dataclass, with no decorator and no options;
- **guardrails** at class creation against declarations that would weaken the enum (subclassing a variant, `@dataclass` over one, `__slots__`);
- **unit variants with exactly one value**;
- **introspection**, so extensions can translate an enum into other forms;
- **extensions**: serialization (Python's counterpart of serde's derive) and `Option`/`Result`;
- **the conventions and configuration** that make the static guarantee hold (see below).

The compiler's refusal is the part Python can't match. Checkers prove exhaustiveness, but only for code that is checked, in a configuration that reports it. A library can't make that mandatory, so the recommended checker configuration and the `assert_never` arm are part of what superenums offers, and the documentation leads with them.

Declaration therefore stays as close to plain dataclasses and a union as possible. A user gives up little by adopting superenums, and gains the extensions on top.

## Scope: the core, then extensions

The core is the machinery for declaring and matching enums: variants, fields, unit variants, introspection, and exhaustiveness support. Ready-made enums such as `Option` and `Result` are **extensions**, built on the core's public API with no special cases.

Keeping them out of the core keeps it small, and its design is driven by what users declare, not by one or two famous enums. Building extensions with only the public API keeps the core honest: anything an extension needs, users get too.

## Type-checker visibility comes before syntax

Whenever a nicer declaration syntax and type-checker visibility conflict, visibility wins.

- **No plugins.** pyright, mypy, and ty must understand superenums using only standard typing features. A plugin ties the library to one checker and its internal APIs. Every plugin-dependent ADT library in the prior art is either dead or limited to mypy, and pyright/Pylance users, probably the largest group of typed-Python users, get nothing from one.
- **Runtime magic is allowed only where checkers can see the result.** A metaclass that builds variants from a compact spec gives a pleasant runtime object that checkers cannot narrow. Without narrowing, there is no exhaustiveness, which is the core promise. A terse syntax that loses that promise is not worth having.

Checkers don't run the code they check. `@dataclass` generates methods at runtime, but checkers never see that code: each checker has its own model of what a dataclass gets, and `dataclass_transform` (PEP 681) lets a library borrow that model. It covers only methods derived from fields. So no runtime decorator can add methods or variants that checkers see, and `Annotated` metadata is invisible to them by design. A variant declared through annotations (`Circle: Annotated[type, ...]`) is rejected as a class pattern by all three checkers. Each variant has to be a `class` statement.

Runtime safety (for example, refusing a declaration that would weaken the enum) is still provided where it costs nothing statically. It backs up the static guarantee; it does not replace it.

## An enum is its union alias

An enum is a `type` alias listing its variants. The variants are ordinary module-level classes:

```python
# shapes.py
class Circle(Variant): radius: float
class Rect(Variant): w: float; h: float
class Empty(Variant): ...

type Shape = Circle | Rect | Empty
```

The alias is the only list of the variants. It is the type used in annotations, and the type a checker proves a `match` exhaustive over.

The enum must be a union because a class hierarchy is open. A type checker can only treat a `match` as exhaustive if it knows every possible type of the value, and from its point of view any module could add a subclass to a class. So a match on a base class is never exhaustive, even when it handles every variant the user wrote. Python has no standard way to declare a hierarchy closed (the `@sealed` proposal is stalled), so a union alias is the only form every checker understands without a plugin.

**Sealed** comes from the alias. Its variant list is fixed where it is written, and the checker sees no others. Nothing at runtime registers or locks an enum.

### The module is the namespace

Variants are reached through their module, as `shapes.Circle`, which reads like Rust's `Shape::Circle` when the module is named after the enum. The module also holds the enum's behaviour (see [Behaviour over an enum is a free function](#behaviour-over-an-enum-is-a-free-function)), so it plays the part of both Rust's `enum` and its `impl` block.

Two enums in one module can't both have a variant called `Empty`. The documented answers are one module per enum, or names that say which enum they belong to (`EmptyShape`). Variants nested in a plain grouping class (`class Shapes: class Circle(Variant): ...`) work in plain Python, but the grouping class can be used as an annotation by mistake, which defeats exhaustiveness silently (see below). The documentation doesn't recommend it.

### A variant can be listed in more than one alias

Nothing stops a variant from appearing in two aliases (`type Shape = Circle | Rect` and `type Round = Circle | Empty`), much as a TypeScript type can appear in two unions. The checker treats each alias as its own closed set, and superenums doesn't track which enum a variant belongs to. The documentation lists each variant in one alias. An extension that needs unique tags checks them per alias, where it is configured.

### No registration call

There is no `seal` or other call after the alias. With one list there is nothing to keep in step, and everything a registration step did at runtime is either covered by the checker or no longer needed:

- A variant left out of the alias is reported wherever it's used as the enum: passing `Triangle(...)` where a `Shape` is expected fails to type-check.
- Unit variants get their single value when the class is created.
- Introspection starts from the alias, which extensions are given anyway (`variants(Shape)`).

What is given up: a runtime guarantee that every variant belongs to exactly one enum, and an error when a variant that is in no enum is constructed. Both were checks against the namespace design's own failure modes.

### Rejected: a namespace class

0.1.0 declared variants as nested classes of a namespace (`class Shapes(Variants): class Circle(Variant): ...`), so they read as `Shapes.Circle`, and the alias listed them a second time (`type Shape = Shapes.Circle | ...`). `Shapes.seal(Shape)` checked that the two lists matched, locked the namespace, and only then allowed construction.

The namespace gave checkers nothing: they learn the variants only from the alias. All it bought was naming, which the module already provides. It cost:

- nesting every variant inside a class body;
- listing every variant twice, plus the `seal` call that checked the two lists matched, and the error for forgetting it;
- a second name per enum that type-checks as an annotation: `def area(s: Shapes)` passes the checker, but no `match` over `s` can be proven exhaustive. This was the design's most likely misuse;
- rules of its own: no subclassing a namespace, no binding the name `seal` in one, introspection functions kept off it so variant names couldn't shadow them.

The namespace design also rejected module-level variants, because two enums in one module couldn't both have an `Empty`. One module per enum is a smaller cost than all of the above.

## A variant is a frozen dataclass

Subclassing `Variant` is the whole declaration. A variant class is a frozen, slotted dataclass whose fields are its annotations: it can be built positionally or by keyword, compares and hashes by variant and field values, has `__match_args__` in field order, and its `repr` uses the qualified name (`Circle(radius=1.0)`).

`Variant` tells type checkers about this through `dataclass_transform` (PEP 681), the standard way to say "subclasses of this class behave like dataclasses". It works the same in every checker with no plugin, so construction signatures, field types, and match patterns are all checked. A `@variant` decorator could carry `dataclass_transform` just as well; the base class is as short to write, and it makes `isinstance(x, Variant)` available to introspection.

Variants are **frozen** because an enum value's variant and fields are what make it valid. If fields could be reassigned after construction, a value checked once could later hold data its variant was never meant to carry, so the "illegal states are unrepresentable" promise would hold only at the moment of creation. Freezing also makes variants safe to hash, share, and use as dict keys. A changed value is a new value (`dataclasses.replace`).

Variants are **slotted** so that no attribute beyond the declared fields can be attached. A variant's shape is exactly what its declaration says.

Variants are **not ordered** by default. Ordering within a variant is natural, but ordering across variants needs a policy (declaration order? an error?) that most enums don't need. Rust likewise orders only with an explicit `derive(PartialOrd)`.

Users don't apply `@dataclass` themselves, and a variant that does, or that tries to opt out of freezing, is rejected when the class is created. One rule for every variant keeps them uniform.

**Keyword-only fields use the standard `dataclasses.KW_ONLY` marker**, not a superenums option. Fields of the same type given positionally can be swapped silently (`ServiceStarted(teller, customer)`), which the first real-world example (a py-ev simulation, `examples/bank_tellers.py`) showed is common in event data. `_: KW_ONLY` in a variant body makes the fields after it keyword-only in construction and in patterns, since they leave `__match_args__`. pyright, mypy and ty all understand it through `dataclass_transform`. It needs no superenums code, keeps the rule that a variant passes no class keywords, and allows a mixed variant (positional fields, then keyword-only ones). Two alternatives were rejected. A `kw_only=True` class keyword would be a second spelling of the marker, and only for whole variants. Keyword-only by default (`kw_only_default=True`) would remove positional construction and patterns where they read well, as in `Rect(w, h)`.

### No inheritance between variants

`Variant` can be subclassed only directly. Subclassing a concrete variant (`class BigCircle(Circle)`) raises `TypeError` when the class is created.

A subclass of a variant would still match that variant's pattern, so exhaustiveness would technically survive. But it adds a state the enum's author never declared, and any fields it adds are silently ignored by every `match` written against the parent. The enum's values would no longer be exactly what its declaration says.

The prevention is runtime-only. A checker would reject these subclasses only if each variant were marked `@final`, and `dataclass_transform` can't apply that implicitly. Requiring users to write `@final` on every variant would add noise to every declaration to catch a rare misuse that already fails at import time. Users may add `@final` themselves.

### Shared data goes in a wrapper, not a base class

A field common to some variants is declared on each, as in Rust, so each variant's fields are always visible in its own declaration.

Data common to every variant, such as an event's timestamp, goes outside the enum, in a type that holds the shared data and the enum value. This is Rust's `struct Event { t: f64, kind: EventKind }`. In Python it is a generic wrapper (`Timed[E]`) or whatever the surrounding code already passes alongside the value: py-ev hands each process `(event, t)`, and none of `examples/bank_tellers.py`'s variants carries a time.

A shared base class with fields (`class Event: t: float`, which each variant inherits) would save repeating them, but the base is not in the alias. `def handle(e: Event)` type-checks, and no `match` over `e` can be proven exhaustive. A base with fields is the most natural annotation an OO habit reaches for, so it would make the guarantee easy to lose and nothing would warn about it. The wrapper declares the shared data once and keeps the union as the type that is matched.

## A unit variant is a class with one cached instance

A unit variant is declared and used like any other variant: it is a class, its value comes from calling it, and it is matched with a class pattern.

```python
class Empty(Variant): ...

e = Empty()          # always the same instance
match s:
    case Empty(): ...
```

Calling a unit variant always returns the same cached instance, so a unit variant has exactly one value, and `x is Empty()` holds for every empty shape. Pickling and copying preserve this: unpickling or deep-copying a unit value gives back the cached instance, not a second one.

A unit variant is one with no fields at all. A variant whose fields all have defaults is not one: `Box()` and `Box(side=2.0)` are different values, so it is never cached. `dataclasses.replace` on a unit value also gives back the cached instance. The instance is made when the class is created.

Rust writes `Shape::Empty` with no call, and a bare `shapes.Empty` value would be closer to it. Checkers don't allow it. They narrow a value pattern such as `case shapes.Empty:` only when the value is a literal or a stdlib enum member that is declared directly. An ordinary singleton object is never narrowed, so a `match` that uses one can never be proven exhaustive. A stdlib enum member does narrow, but only when the union alias names it through `Literal[...]` on the stdlib enum's own declaration, not on a re-export. The user would have to declare a separate stdlib enum to hold each enum's unit variants and spell the alias with `Literal`. The library cannot generate any of that, because checkers recognise only enum members declared in source. The parentheses are the cost of exhaustiveness.

Treating every variant as a class also keeps the model uniform. Every value is made by a call and every pattern is a class pattern, so nothing depends on whether a variant has fields.

**Trap: `case Empty:` without parentheses** is not a class pattern. A bare name is a capture pattern, which matches anything (Python rejects it unless it is the last arm), and a dotted name (`case shapes.Empty:`) is a value pattern that compares against the class itself and never matches. In checked code the checker reports the `match` as non-exhaustive. In unchecked code it fails silently, so the documentation calls it out prominently. A runtime guard, such as making the class compare equal to its instance, would add behaviour checkers can't model, so there isn't one.

## Generic enums: type parameters on the variants

An enum is generic when its variants are. Each variant that carries type-dependent data declares its own type parameters, and the alias connects them:

```python
class Leaf[T](Variant):  value: T
class Node[T](Variant):  left: "Tree[T]"; right: "Tree[T]"
class Empty(Variant): ...

type Tree[T] = Leaf[T] | Node[T] | Empty
```

Variants whose data doesn't depend on a type parameter stay non-generic. A unit variant such as `Empty` fits every `Tree[T]`, just as Rust's `None` fits every `Option<T>`. Each variant's type parameters are independent until the alias relates them. By convention they use the same names across an enum, so the alias reads naturally.

The cost is repeating the type parameters on every variant that uses them. This is the only form checkers understand: narrowing in `case Leaf(value=v)` gives `v: T`, mismatched type arguments are rejected, and a missing variant is reported as a non-exhaustive match.

Recursive variants name the alias in quoted annotations. Nothing evaluates variant annotations when the class is created, so the alias can be defined after the variants that refer to it.

## Behaviour over an enum is a free function

Behaviour that spans an enum's variants is written as an ordinary function over the enum, with one `match` inside, in the enum's module. It is the Python form of Rust's `impl Shape { fn area(&self) { match self { … } } }`:

```python
# shapes.py
def area(s: Shape) -> float:
    match s:
        case Circle(radius=r): return 3.14 * r * r
        case Rect(w=w, h=h): return w * h
        case Empty(): return 0.0
        case _: assert_never(s)
```

Callers write `shapes.area(s)`. The module gives the operations the same grouping `impl` gives them in Rust: `shapes.area` doesn't clash with another enum's `area`, and `shapes.` lists them in an editor.

This is the only form that is both fully visible to checkers and free of boilerplate. Because the parameter is the union, the `match` is checked for exhaustiveness. Adding a variant makes every such function fail to type-check until it handles the new variant, which is exactly how Rust behaves.

What a free function can't do is be called as a method. Method syntax (`s.scale(2).area()`) is a convenience. Python does need methods for its protocols: `str()`, operators, `bool()`, `len()` and iteration look them up on the value's class, and a `Protocol` is satisfied only by methods. For those, superenums offers no machinery, and plain Python has two forms:

- **Methods on each variant.** Calling `s.area()` on the union type-checks only if every variant defines `area`. pyright, mypy and ty each report a variant that doesn't, wherever the method is called on the union. This keeps the guarantee, with the behaviour split across the variants.
- **A mixin whose methods pass `self` on to the free function**, with a `cast` to the union. Checkers reject annotating `self` as the union in a mixin, since the union isn't a supertype of the mixin (pyright and mypy both report it), so the cast is unavoidable. The mixin is also a base class that can be used as an annotation by mistake.

Neither form is needed for most behaviour, and the documentation leads with the free function. Generating methods was rejected: a runtime generator is invisible to checkers, and source or stub generation at build time needs a build step and a check that the output is current, which costs more than method syntax is worth.

## The standard match ends in `assert_never`

Every `match` over an enum in the documentation ends with a catch-all arm that calls `typing.assert_never`:

```python
match s:
    case Circle(radius=r): ...
    case Rect(w=w, h=h): ...
    case Empty(): ...
    case _: assert_never(s)
```

This one idiom guards in both worlds. Statically, every checker reports any variant that can reach the arm. At runtime, a value that gets through anyway (from unchecked code, or a variant added without re-checking) raises an error naming that value.

The arm is needed because checkers otherwise report a missing variant only indirectly. In default settings, pyright, mypy, and ty each catch a non-exhaustive `match` only through a consequence such as a missing return value. A `match` in a function that returns nothing, or one followed by more code, misses a variant silently. Pyright's `reportMatchNotExhaustive` reports non-exhaustive matches directly, and the documentation recommends enabling it, but it is off outside strict mode and has no equivalent in the other checkers. The `assert_never` arm makes the guarantee independent of return types, checker choice, and configuration.

A wildcard arm that does something else (`case _: pass`) is a legitimate choice for a `match` that cares about only some variants. It opts that `match` out of exhaustiveness, visibly, and adding a variant leaves it unreported. superenums doesn't forbid it. Where every variant should force a decision, the ignored variants are listed explicitly in an or-pattern arm before the standard arm. The guide presents the two forms as a deliberate choice. In a discrete event simulation (`examples/bank_tellers.py`), where every process receives every event, both forms appear naturally.

**Matching several enums at once** (`match (state, event):`, the shape of a state machine's transition table) is checked by pyright and ty: a complete set of tuple arms passes, and a missing combination is reported (pyright names it, e.g. `tuple[Busy, Finish]`). mypy doesn't narrow a tuple of unions, so it reports even a complete match as non-exhaustive. Nested `match` statements, one enum at a time, are checked by all three, and the documentation shows that form where mypy matters.

The core has no handler-based matching API (such as `match_shape(s, circle=..., rect=...)`), although it would give an expression form. A checker can't verify such a handler set without a plugin: keyword names derived from variant names are invisible to it, a mapping keyed by variant class can't be checked for completeness, and handler callables lose the narrowed types a `case` gives. It would be a second, weaker way to do what the `match` statement already does with full checking. An expression-form helper can be added later as an extension.

## superenums complements the stdlib enum

superenums is for enums with data. When no variant carries fields, a **stdlib enum** is the better tool. Its members need no parentheses, checkers narrow them through `Literal` with no alias, and it comes with iteration, names, values, and broad serializer support. The documentation steers users there and shows the two used together, with a stdlib enum as a field type:

```python
class Color(enum.Enum):
    RED = enum.auto()
    GREEN = enum.auto()

class Pen(Variant): color: Color; width: float
class Eraser(Variant): width: float

type Stroke = Pen | Eraser
```

An enum made only of unit variants is still allowed. Rejecting it would turn an ordinary refactor, such as removing the last variant that carries data, into a forced rewrite as a different kind of enum.

## Introspection is public; serialization is an extension

The core exposes a small, read-only description of each enum, starting from its alias:

- an enum's variants, in the order the alias lists them (`variants(Shape)`). Given an alias that names anything other than variant classes, it raises an error. A subscripted generic variant (`Leaf[T]`, `Leaf[int]`) counts as its variant class;
- a variant's name: its plain class name (`"Circle"`), the natural tag for serialization;
- a variant's fields: just the standard `dataclasses.fields`, since every variant is a dataclass.

Introspection is public because extensions use only the public API, and any extension that translates an enum into another form, such as a serialization schema, needs exactly this description. It is offered as module-level functions, never as attributes on variant classes, where the names could collide with a variant's fields.

Serialization is an extension, not part of the core. Pydantic, msgspec, and cattrs each already have their own tagged-union mechanism. An extension maps an enum onto each one, given its alias, using the variant name as the default tag. Because a variant can come from any module, two variants in one alias can share a name; an extension checks that its tags are unique when it is configured for an alias. Putting serialization in the core would mean choosing among those libraries and depending on them.

## Serialization: the tag goes inside the object

Every serialization extension writes a value the same way: an object holding the variant's fields plus a **tag** naming the variant.

```python
{"type": "Circle", "radius": 1.0}
{"type": "Empty"}  # a unit variant is just its tag
```

The tag key defaults to `"type"` and can be changed per alias. The tag value is `variant_name`. This is serde's internally tagged form (`#[serde(tag = "type")]`), and it is the native tagged-union form of pydantic (a discriminator field), msgspec (`tag_field`) and cattrs (`configure_tagged_union`), so each extension maps onto its library's own mechanism. It is also how JSON APIs commonly tag their objects. Loading a unit variant returns its cached instance.

A variant with a field of the same name as the tag key is an error when the extension is configured, since its tag would overwrite the field.

Rejected: serde's default externally tagged form, `{"Circle": {"radius": 1.0}}`. It cannot collide with a field, but none of the three libraries supports it natively, so every extension would carry its own codec.

### cattrs: hooks over the converter's own

`superenums.cattrs.configure(Shape, converter, key="type")` registers hook factories for the alias, its specialisations (`Tree[int]`) and the union it names. The hooks add or read the tag and delegate the fields to the converter's own hook for each variant (`Leaf[int]`), looked up on first use so a recursive enum's hooks can refer to themselves. cattrs' `configure_tagged_union` was not used: it fails on an alias naming one variant, can't substitute a generic alias's type arguments, and reports an unknown tag as a bare `KeyError`.

Checkers reject the alias as `structure`'s target (typed `type[T]`), and accept the union it names (`Shape.__value__`, typed `Any`), so the hooks match that union too. Otherwise a type-checked caller would silently skip the tag.

### Packaging: extras, not separate distributions

The extensions ship in the `superenums` distribution as modules (`superenums.cattrs`, `superenums.pydantic`, `superenums.msgspec`), each needing its library through an extra (`superenums[pydantic]`). The core keeps zero dependencies: nothing outside an extension's own module imports its library, and a test checks that `superenums` imports with none of them installed.

### pydantic: a plain alias just works

Given a union of plain dataclasses, pydantic writes no tag. Two unit variants both become `{}`, and same-shaped variants load as whichever comes first, without any error. A marker the user has to remember (`Annotated[Shape, ...]`) would leave every forgotten one losing data silently. So `Variant` defines `__get_pydantic_core_schema__`, and a plain `Shape` in a model writes and reads the tag. The method imports pydantic only when pydantic calls it, so the core still doesn't depend on pydantic. This is the one place the core knows about a serialization library: it is justified by the silent data loss, and it still uses only the public introspection API.

The hook sees one variant at a time, never the alias, so it can't do everything. It always uses the default `"type"` key. pydantic tries the variants in turn instead of dispatching on the tag, so validation errors list every variant. And it can't check tags are unique. `Annotated[Shape, superenums.pydantic.Tagged(key="kind")]` opts into a real discriminated union over the alias: a custom key, dispatch on the tag with errors for that variant only, and the uniqueness check.

When dumping, pydantic picks a union member by trying each one's serializer. Each variant's serializer must refuse a value of another variant (raise `PydanticSerializationUnexpectedValue`), or the first variant's serializer accepts everything and writes the wrong tag.

### msgspec: open

msgspec can't load a union of dataclasses at all ("Type unions may not contain more than one dataclass or attrs type"). Two approaches remain to be prototyped: generating a matching tagged `msgspec.Struct` per variant (fast, and gives JSON Schema), or decoding to raw data, dispatching on the tag and calling `msgspec.convert`.

## Python 3.12 and later

superenums requires Python 3.12+. Its API and documentation use PEP 695 syntax throughout (`class Some[T](Variant):`, `type Shape = ...`).

Generic enums such as `Tree[T]` are part of the core, and the planned `Option[T]` and `Result[T, E]` extensions depend on them. With PEP 695 generic syntax they read the way Rust users expect, without the `TypeVar` boilerplate that clutters every signature. All three supported type checkers handle that syntax well. `type` aliases are also evaluated lazily, which suits enums that refer to themselves.

An older floor would mean writing every generic example twice or settling for the noisier form. 3.10, the earliest version with `match`, is also at end of life. A 3.14 floor would remove the need for quoted forward references in recursive variants (deferred annotations, PEP 649), but it would exclude most production codebases for a small convenience. Quoted annotations (`left: "Tree[T]"`) work with every checker on 3.12 and 3.13.
