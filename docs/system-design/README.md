# superenums system design

superenums brings Rust-style enums (sum types whose variants carry data) to Python. It is a production library for typed codebases.

## Core promise

Illegal states are unrepresentable, and the user's type checker proves that a `match` over an enum is exhaustive.

Static proof is what matters here. Runtime checks find a missing case only when that code path runs. A type checker finds it everywhere, including the moment a new variant is added. That is what makes Rust enums safe to change, and it is the property no maintained Python library offers today without a plugin (see [prior art](../prior-art.md)).

## Scope: the core, then extensions

The core is the machinery for declaring and matching enums: namespaces, variants, fields, sealing, and exhaustiveness support. Ready-made enums such as `Option` and `Result` are **extensions**, built on the core's public API with no special cases.

Keeping them out of the core keeps it small, and its design is driven by what users declare, not by one or two famous enums. Building extensions with only the public API keeps the core honest: anything an extension needs, users get too.

## Type-checker visibility comes before syntax

Whenever a nicer declaration syntax and type-checker visibility conflict, visibility wins.

- **No plugins.** pyright, mypy, and ty must understand superenums using only standard typing features. A plugin ties the library to one checker and its internal APIs. Every plugin-dependent ADT library in the prior art is either dead or limited to mypy, and pyright/Pylance users, probably the largest group of typed-Python users, get nothing from one.
- **Runtime magic is allowed only where checkers can see the result.** A metaclass that builds variants from a compact spec gives a pleasant runtime object that checkers cannot narrow. Without narrowing, there is no exhaustiveness, which is the core promise. A terse syntax that loses that promise is not worth having.

Runtime safety (for example, refusing an incomplete set of match handlers) is still provided where it costs nothing statically. It backs up the static guarantee; it does not replace it.

## An enum has two names: a namespace and a union

A declared enum has two parts:

- a **namespace class** that holds the variants as nested classes: `Shapes.Circle`, `Shapes.Rect`;
- a **union alias** listing every variant, used in annotations: `type Shape = Shapes.Circle | Shapes.Rect`.

```python
class Shapes(Variants):
    class Circle(Variant): radius: float
    class Rect(Variant): w: float; h: float

type Shape = Shapes.Circle | Shapes.Rect
Shapes.seal(Shape)
```

The split exists because static exhaustiveness requires that annotations name a union. A type checker can only treat a `match` as exhaustive if it knows every possible type of the value. A class hierarchy is open: from the checker's point of view, any module could add a subclass. So a match on a base class is never exhaustive, even when it handles every variant the user wrote. Python has no standard way to declare a hierarchy closed (the `@sealed` proposal is stalled), so a union alias is the only form every checker understands without a plugin.

A single name can't serve both purposes. A union alias has no attributes, so `Shape.Circle` is not possible on it. A class can carry the variants but is never exhaustive. Making the variants top-level classes with no namespace would drop the second name, but at a cost: variant names from different enums in the same module would clash (two `Empty` variants), and the Rust-style `Shape.Circle` reading would be lost.

The variant list is written twice, once in the namespace class and once in the alias. That repetition is the cost of not having `@sealed`. Sealing (below) checks that the alias names exactly the namespace's variants, so a variant added to one but not the other fails at import time and never drifts silently. If `@sealed` is ever standardized, the namespace class itself could act as the annotation type, and the alias would become optional.

**Annotating with the namespace class is discouraged.** `def area(s: Shapes)` type-checks, but no `match` over `s` can ever be proven exhaustive, and the checker reports this as a non-exhaustive match or a missing return. The documentation always uses the union alias in annotations. This is the most likely misuse of the design, so stronger prevention may be needed.

## Sealing connects the alias to the namespace

`Shapes.seal(Shape)`, written right after the alias, is what makes a declaration an enum. It:

1. checks that the alias's variants are exactly the namespace's variants, no more and no fewer;
2. locks the namespace so no variant can be added afterwards;
3. marks the enum ready, after which its variants can be constructed.

The library cannot find the alias on its own, because the namespace and the alias are separate statements and neither refers to the other at class-creation time. Declaring the alias inside the namespace body would let the library find it automatically, and for non-generic enums every checker accepts that. Generic enums break it. Inside the class body, a generic alias cannot refer to sibling variants by their bare names, so they must be qualified with the namespace name. Re-exporting the nested alias at module level (`Tree = Trees.Tree`) loses its type parameters in some checkers, and narrowing through a nested generic alias isn't supported everywhere. A module-level alias plus an explicit `seal` behaves the same for generic and non-generic enums in every checker.

An explicit call can be forgotten, so constructing any variant of an unsealed namespace raises an error naming the missing `seal` call. A forgotten seal fails on first use rather than silently skipping the drift check.

Sealing is how the glossary's **Sealed** property is enforced at runtime. Static closure comes from the alias, since the checker sees only the variants it lists.

### No subclassing beyond the declaration

`Variant` and `Variants` can be subclassed only directly. Subclassing a concrete variant (`class BigCircle(Shapes.Circle)`) or a concrete namespace (`class MoreShapes(Shapes)`) raises `TypeError` when the class is created.

A subclass of a variant would still match that variant's pattern, so exhaustiveness would technically survive. But it adds a state the enum's author never declared, and any fields it adds are silently ignored by every `match` written against the parent. Subclassing a namespace makes it unclear which enum a variant belongs to. Either way, the enum's values would no longer be exactly what its declaration says.

A variant declared outside any namespace needs no rule of its own. It belongs to no sealed namespace, so it can't be constructed.

The prevention is runtime-only. A checker would reject these subclasses only if each variant were marked `@final`, and `dataclass_transform` can't apply that implicitly. Requiring users to write `@final` on every variant would add noise to every declaration to catch a rare misuse that already fails at import time. Users may add `@final` themselves.

Since variants can't inherit from one another, they don't share fields through inheritance. A field common to several variants is declared on each, as in Rust, so each variant's fields are always visible in its own declaration.

## A variant is a frozen dataclass

Subclassing `Variant` is the whole declaration. A variant class is a frozen, slotted dataclass whose fields are its annotations: it can be built positionally or by keyword, compares and hashes by variant and field values, has `__match_args__` in field order, and its `repr` uses the qualified name (`Shapes.Circle(radius=1.0)`).

`Variant` tells type checkers about this through `dataclass_transform` (PEP 681), the standard way to say "subclasses of this class behave like dataclasses". It works the same in every checker with no plugin, so construction signatures, field types, and match patterns are all checked.

Variants are **frozen** because an enum value's variant and fields are what make it valid. If fields could be reassigned after construction, a value checked once could later hold data its variant was never meant to carry, so the "illegal states are unrepresentable" promise would hold only at the moment of creation. Freezing also makes variants safe to hash, share, and use as dict keys. A changed value is a new value (`dataclasses.replace`).

Variants are **slotted** so that no attribute beyond the declared fields can be attached. A variant's shape is exactly what its declaration says.

Variants are **not ordered** by default. Ordering within a variant is natural, but ordering across variants needs a policy (declaration order? an error?) that most enums don't need. Rust likewise orders only with an explicit `derive(PartialOrd)`.

Users don't apply `@dataclass` themselves, and a variant that does, or that tries to opt out of freezing, is rejected when the class is created. One rule for every variant keeps them uniform.

## A unit variant is a class with one cached instance

A unit variant is declared and used like any other variant: it is a class, its value comes from calling it, and it is matched with a class pattern.

```python
class Shapes(Variants):
    class Empty(Variant): ...

e = Shapes.Empty()          # always the same instance
match s:
    case Shapes.Empty(): ...
```

Calling a unit variant always returns the same cached instance, so a unit variant has exactly one value, and `x is Shapes.Empty()` holds for every empty shape. Pickling and copying preserve this: unpickling or deep-copying a unit value gives back the cached instance, not a second one.

A unit variant is one with no fields at all. A variant whose fields all have defaults is not one: `Box()` and `Box(side=2.0)` are different values, so it is never cached. `dataclasses.replace` on a unit value also gives back the cached instance. The instance is cached when the namespace is sealed, so an unsealed unit variant refuses construction like any other variant.

Rust writes `Shape::Empty` with no call, and a bare `Shapes.Empty` value would be closer to it. Checkers don't allow it. They narrow a value pattern such as `case Shapes.Empty:` only when the value is a literal or a stdlib enum member that is declared directly. An ordinary singleton object is never narrowed, so a `match` that uses one can never be proven exhaustive. A stdlib enum member does narrow, but only when the union alias names it through `Literal[...]` on the stdlib enum's own declaration, not on a re-export. The user would have to declare a separate stdlib enum to hold each enum's unit variants, re-export each member on the namespace, and spell the alias with `Literal`. The library cannot generate any of that, because checkers recognise only enum members declared in source. The parentheses are the cost of exhaustiveness.

Treating every variant as a class also keeps the model uniform. Every value is made by a call and every pattern is a class pattern, so nothing depends on whether a variant has fields.

**Trap: `case Shapes.Empty:` without parentheses** is a value pattern that compares against the class itself and never matches. In checked code the checker reports the `match` as non-exhaustive. In unchecked code it fails silently, so the documentation calls it out prominently. A runtime guard, such as making the class compare equal to its instance, would add behaviour checkers can't model, so there isn't one.

## Generic enums: type parameters on the variants

An enum is generic when its variants are. Each variant that carries type-dependent data declares its own type parameters, and the union alias connects them:

```python
class Trees(Variants):
    class Leaf[T](Variant):  value: T
    class Node[T](Variant):  left: "Tree[T]"; right: "Tree[T]"
    class Empty(Variant): ...

type Tree[T] = Trees.Leaf[T] | Trees.Node[T] | Trees.Empty
Trees.seal(Tree)
```

The namespace is never generic. Each variant is a class in its own right, and a type parameter on the namespace does not make the nested classes generic: `Trees[int].Leaf` is not a type, and constructing `Leaf(1)` gives the checker nothing to bind. Type parameters must live on the classes that are actually instantiated.

Variants whose data doesn't depend on a type parameter stay non-generic. A unit variant such as `Trees.Empty` fits every `Tree[T]`, just as Rust's `None` fits every `Option<T>`. Each variant's type parameters are independent until the alias relates them. By convention they use the same names across an enum, so the alias reads naturally.

The cost is repeating the type parameters on every variant that uses them. This is the only form checkers understand: narrowing in `case Trees.Leaf(value=v)` gives `v: T`, mismatched type arguments are rejected, and a missing variant is reported as a non-exhaustive match.

The seal check compares variant classes regardless of their type arguments, so `Trees.Leaf[T]` in the alias counts as `Trees.Leaf`. Validating type arguments is the checker's job.

## Behaviour over an enum is a free function

Behaviour that spans an enum's variants is written as an ordinary function over the enum, with one `match` inside, the Python form of Rust's `impl Shape { fn area(&self) { match self { … } } }`:

```python
def area(s: Shape) -> float:
    match s:
        case Shapes.Circle(radius=r): return 3.14 * r * r
        case Shapes.Rect(w=w, h=h): return w * h
```

This is the only form that is both fully visible to checkers and free of boilerplate. Because the parameter is the union, the `match` is checked for exhaustiveness. Adding a variant makes every such function fail to type-check until it handles the new variant, which is exactly how Rust behaves.

A method version, `s.area()`, would need every variant class to visibly define `area`, because `s` is a union. The namespace class can't supply it. A class nested in the namespace's body can't inherit from the namespace, which doesn't yet exist when the nested class is created. A runtime step that copies methods from the namespace onto the variants would be invisible to checkers, so `s.area()` would fail to type-check. The workable method form is a separate mixin class that every variant inherits. It needs a third name per enum and a mixin listed on every variant. It also needs a cast inside each method, because checkers reject annotating `self` as the union, and without the cast the `match` can't be proven exhaustive. That is too much ceremony for a pattern the free function already expresses.

Users are still free to define per-variant methods, or a mixin, in plain Python. superenums simply provides no machinery for it. The namespace therefore holds only variants.

## The standard match ends in `assert_never`

Every `match` over an enum in the documentation ends with a catch-all arm that calls `typing.assert_never`:

```python
match s:
    case Shapes.Circle(radius=r): ...
    case Shapes.Rect(w=w, h=h): ...
    case _: assert_never(s)
```

This one idiom guards in both worlds. Statically, every checker reports any variant that can reach the arm. At runtime, a value that gets through anyway (from unchecked code, or a variant added without re-checking) raises an error naming that value.

The arm is needed because checkers otherwise report a missing variant only indirectly. In default settings, pyright, mypy, and ty each catch a non-exhaustive `match` only through a consequence such as a missing return value. A `match` in a function that returns nothing, or one followed by more code, misses a variant silently. Pyright's `reportMatchNotExhaustive` reports non-exhaustive matches directly, and the documentation recommends enabling it, but it is off outside strict mode and has no equivalent in the other checkers. The `assert_never` arm makes the guarantee independent of return types, checker choice, and configuration.

The core has no handler-based matching API (such as `Shapes.match(s, circle=..., rect=...)`), although it would give an expression form. A checker can't verify such a handler set without a plugin: keyword names derived from variant names are invisible to it, a mapping keyed by variant class can't be checked for completeness, and handler callables lose the narrowed types a `case` gives. It would be a second, weaker way to do what the `match` statement already does with full checking. An expression-form helper can be added later as an extension.

## superenums complements the stdlib enum

superenums is for enums with data. When no variant carries fields, a **stdlib enum** is the better tool. Its members need no parentheses, checkers narrow them through `Literal` with no alias or `seal`, and it comes with iteration, names, values, and broad serializer support. The documentation steers users there and shows the two used together, with a stdlib enum as a field type:

```python
class Color(enum.Enum):
    RED = enum.auto()
    GREEN = enum.auto()

class Strokes(Variants):
    class Pen(Variant): color: Color; width: float
    class Eraser(Variant): width: float
```

An enum made only of unit variants is still allowed. Rejecting it would turn an ordinary refactor, such as removing the last variant that carries data, into a forced rewrite as a different kind of enum.

## Introspection is public; serialization is an extension

The core exposes a small, read-only description of each enum:

- a namespace's variants, in declaration order;
- its sealed union alias;
- from a variant class or value, its namespace;
- a variant's name: its plain class name (`"Circle"`), the natural tag for serialization;
- a variant's fields: just the standard `dataclasses.fields`, since every variant is a dataclass.

Introspection is public because extensions use only the public API, and any extension that translates an enum into another form, such as a serialization schema, needs exactly this description. Introspection is offered as functions or methods, never as plain class attributes, because attribute names on a namespace would collide with variant names. An enum can easily have a variant called `Alias` or `Variants`.

Serialization is an extension, not part of the core. Pydantic, msgspec, and cattrs each already have their own tagged-union mechanism. An extension maps an enum onto each one, using the variant name as the default tag. Putting serialization in the core would mean choosing among those libraries and depending on them.

## Python 3.12 and later

superenums requires Python 3.12+. Its API and documentation use PEP 695 syntax throughout (`class Option[T]:`, `type Shape = ...`).

Generic enums such as `Tree[T]` are part of the core, and the planned `Option[T]` and `Result[T, E]` extensions depend on them. With PEP 695 generic syntax they read the way Rust users expect, without the `TypeVar` boilerplate that clutters every signature. All three supported type checkers handle that syntax well. `type` aliases are also evaluated lazily, which suits enums that refer to themselves.

An older floor would mean writing every generic example twice or settling for the noisier form. 3.10, the earliest version with `match`, is also at end of life. A 3.14 floor would remove the need for quoted forward references in recursive variants (deferred annotations, PEP 649), but it would exclude most production codebases for a small convenience. Quoted annotations (`left: "Expr"`) work with every checker on 3.12 and 3.13.
