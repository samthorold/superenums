# The superenums guide

This guide shows how to write enums with superenums, the way the library is designed to be used. Every example here runs as part of the test suite.

The words used throughout:

- **enum**: a closed type whose values are exactly one of a fixed set of variants. Here, always a superenums enum, written as a union alias (`Shape`).
- **namespace**: the class that holds an enum's variants (`Shapes`). The namespace is not the enum.
- **variant**: one alternative of an enum (`Shapes.Circle`). A **unit variant** has no fields.
- **field**: a named, typed piece of data on a variant (`radius`).
- **sealed**: every enum's set of variants is fixed where it is declared.
- **stdlib enum**: Python's own `enum.Enum`, always called that, never a bare "enum".

The reasons behind the design are in [the system design](system-design/README.md). This guide links there rather than repeating them.

## Declaring an enum

An enum is declared in three statements: a namespace with the variants, a union alias, and a `seal` call.

```python
from superenums import Variant, Variants


class Shapes(Variants):  # 1. the namespace holds the variants
    class Circle(Variant):
        radius: float

    class Rect(Variant):
        w: float
        h: float

    class Empty(Variant): ...  # a unit variant: no fields


type Shape = Shapes.Circle | Shapes.Rect | Shapes.Empty  # 2. the enum
Shapes.seal(Shape)  # 3. connect the two

circle = Shapes.Circle(radius=1.0)
rect = Shapes.Rect(2.0, 3.0)  # fields can be given positionally, in order
assert rect.w == 2.0
```

1. **The namespace** subclasses `Variants`. Each variant is a class nested inside it that subclasses `Variant`, and its annotations are its fields.
2. **The alias** is a `type` statement listing every variant. It is the enum: the type you annotate with.
3. **`seal`** checks that the alias lists exactly the namespace's variants, then locks the namespace and allows its variants to be constructed. Write it right after the alias.

The variants are listed twice, once in the namespace and once in the alias. A type checker can prove a `match` exhaustive only over a union, while variants are reached through a class (`Shapes.Circle`), and no single Python name can be both ([why](system-design/README.md#an-enum-has-two-names-a-namespace-and-a-union)). `seal` keeps the two lists from drifting apart: a variant missing from the alias, or one the alias lists that the namespace doesn't, fails at import time.

```python
from superenums import SuperEnumError, Variant, Variants


class Shapes(Variants):
    class Circle(Variant):
        radius: float

    class Rect(Variant):
        w: float
        h: float


type Shape = Shapes.Circle  # Rect is missing

try:
    Shapes.seal(Shape)
except SuperEnumError as error:
    assert "missing Shapes.Rect" in str(error)
else:
    raise AssertionError("seal accepted an incomplete alias")
```

A forgotten `seal` doesn't go unnoticed either: constructing a variant of an unsealed namespace raises a `SuperEnumError` naming the missing call.

```python
from superenums import SuperEnumError, Variant, Variants


class Shapes(Variants):
    class Circle(Variant):
        radius: float


type Shape = Shapes.Circle

try:
    Shapes.Circle(radius=1.0)
except SuperEnumError as error:
    assert "Shapes.seal(<alias>)" in str(error)
else:
    raise AssertionError("an unsealed variant was constructed")
```

`SuperEnumError` is a `TypeError`. superenums raises it for every declaration or use it doesn't allow, including subclassing a variant or a namespace, applying `@dataclass` to a variant, or naming something in a namespace `seal`.

### Naming: a plural namespace, a singular enum

Name the namespace in the plural and the enum in the singular: `Shapes` holds the variants, and a `Shape` is one value. The pair reads naturally in code: you build a value with `Shapes.Circle(radius=1.0)` and accept one with `s: Shape`.

If a long namespace name crowds the code that builds and matches values, bind a short name to it. pyright, mypy and ty treat the short name as the namespace, so matches through it are still proven exhaustive:

```python
from typing import assert_never

from superenums import Variant, Variants


class BankEvents(Variants):
    class CustomerArrived(Variant):
        customer: int

    class DoorsClosed(Variant): ...


type BankEvent = BankEvents.CustomerArrived | BankEvents.DoorsClosed
BankEvents.seal(BankEvent)

E = BankEvents


def describe(event: BankEvent) -> str:
    match event:
        case E.CustomerArrived(customer=c):
            return f"customer {c} arrives"
        case E.DoorsClosed():
            return "doors close"
        case _:
            assert_never(event)


assert describe(E.CustomerArrived(customer=1)) == "customer 1 arrives"
```

Annotate with the enum as usual (`event: BankEvent`). The short name is the namespace, so annotating with it falls into the same trap as annotating with `BankEvents` ([below](#the-standard-match-ends-in-case-_-assert_nevers)).

## Behaviour is a free function with one `match`

Behaviour over an enum is an ordinary function that takes the enum and contains one `match`. It is the Python form of a Rust `impl` block whose method matches on `self`.

```python
from typing import assert_never

from superenums import Variant, Variants


class Shapes(Variants):
    class Circle(Variant):
        radius: float

    class Rect(Variant):
        w: float
        h: float

    class Empty(Variant): ...


type Shape = Shapes.Circle | Shapes.Rect | Shapes.Empty
Shapes.seal(Shape)


def area(s: Shape) -> float:
    match s:
        case Shapes.Circle(radius=r):  # by keyword
            return 3.14159 * r * r
        case Shapes.Rect(w, h):  # or positionally, in field order
            return w * h
        case Shapes.Empty():
            return 0.0
        case _:
            assert_never(s)


def describe(s: Shape) -> str:
    match s:
        case Shapes.Circle(radius=r) if r > 10:  # guards work as usual
            return "a big circle"
        case Shapes.Circle():
            return "a circle"
        case Shapes.Rect(w, h) if w == h:
            return "a square"
        case Shapes.Rect():
            return "a rectangle"
        case Shapes.Empty():
            return "nothing"
        case _:
            assert_never(s)


assert area(Shapes.Rect(2.0, 3.0)) == 6.0
assert describe(Shapes.Rect(2.0, 2.0)) == "a square"
assert describe(Shapes.Circle(radius=20.0)) == "a big circle"
```

Inside each arm the checker narrows `s` to that variant, so its fields are typed: `r` is a `float`. Add a variant to `Shapes` and `Shape`, and every function like these fails to type-check until it handles the new variant.

superenums has no machinery for methods on an enum: a method form needs a mixin on every variant and a cast in every method before a checker can verify it ([why](system-design/README.md#behaviour-over-an-enum-is-a-free-function)). You can still write methods on individual variants in plain Python.

### The standard match ends in `case _: assert_never(s)`

End every `match` over an enum with `case _: assert_never(s)`, as above. It guards in two places:

- **Statically**, if any variant can reach that arm, the checker reports an error on that line. pyright, mypy, and ty all do, whatever the function returns and however the checker is configured. Without the arm, a checker notices a missing variant only through a consequence such as a missing return value, so a `match` in a function that returns `None`, or one followed by more code, misses a variant silently.
- **At runtime**, a value that gets past every `case` anyway (from unchecked code, say) raises an `AssertionError` naming the value, instead of falling through.

If you use pyright, also enable [`reportMatchNotExhaustive`](https://microsoft.github.io/pyright/#/configuration?id=reportMatchNotExhaustive), which reports a non-exhaustive `match` directly. It is off outside strict mode:

```toml
# pyrightconfig.json uses the same key
[tool.pyright]
reportMatchNotExhaustive = "error"
```

mypy and ty have no equivalent, which is why the `assert_never` arm is the standard everywhere.

> [!IMPORTANT]
> **Annotate with the enum, never the namespace.** Write `def area(s: Shape)`, not `def area(s: Shapes)`. `Shapes` is a class, and a class can always gain subclasses, so no `match` over a `Shapes` is ever proven exhaustive, even one that handles every variant. A variant is not a subclass of its namespace either, so pyright in strict mode reports every `case Shapes.Circle()` as a pattern that can never match. Every checker reports the `assert_never` arm, so the mistake shows up as an error there, not silently, but the fix is always the same: annotate with the alias.

The same holds wherever an enum appears in a type: `list[Shape]`, `dict[str, Shape]`, `Shape | None`, a field typed with another enum.

### Handling only some variants

A function often cares about only a few variants: a logger that reports only errors, or a process in a simulation that reacts only to arrivals. There are two ways to write the rest, and which one you use is a deliberate choice.

**List the rest in an ignore arm**, then end with the standard `assert_never` arm:

```python
from typing import assert_never

from superenums import Variant, Variants


class Events(Variants):
    class Arrived(Variant):
        customer: int

    class ServiceStarted(Variant):
        customer: int

    class ServiceFinished(Variant):
        customer: int

    class DoorsClosed(Variant): ...


type Event = (
    Events.Arrived | Events.ServiceStarted | Events.ServiceFinished | Events.DoorsClosed
)
Events.seal(Event)


def queue_length(events: list[Event]) -> int:
    waiting = 0
    for event in events:
        match event:
            case Events.Arrived():
                waiting += 1
            case Events.ServiceStarted():
                waiting -= 1
            case Events.ServiceFinished() | Events.DoorsClosed():
                pass  # no effect on the queue
            case _:
                assert_never(event)
    return waiting


assert (
    queue_length([Events.Arrived(1), Events.Arrived(2), Events.ServiceStarted(1)]) == 1
)
```

Add a variant and this `match` fails to type-check until the new variant is put in an arm, even if that arm is the ignore arm. Each such function makes its own decision about the new variant. Use this form when the function is only correct if it sees every variant that matters to it. Here, a new `CustomerLeftQueue` variant has to reduce the count.

**Or end with `case _: pass`** (or `case _: return None`, or whatever "not interested" means in that function) in place of the `assert_never` arm. A new variant then falls into the wildcard, and no checker reports it. Use this form when the function stays correct whatever variants are added, such as a filter that picks out one variant.

Neither form is a loophole. The wildcard form opts that one `match` out of exhaustiveness checking, and it's visible in the code. What superenums guarantees is that the explicit form is checked, not that every `match` uses it. The examples in this guide all use the standard arm.

## Variant values

A variant is a frozen, slotted dataclass. Its values are immutable, compare and hash by variant and field values, and have a readable `repr`. To change a value, make a new one with `dataclasses.replace`.

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
assert circle == Shapes.Circle(1.0)
assert repr(circle) == "Shapes.Circle(radius=1.0)"
# different variants never compare equal, even with identical fields
assert len({circle, Shapes.Circle(1.0), Shapes.Square(1.0)}) == 2

bigger = dataclasses.replace(circle, radius=2.0)
assert bigger == Shapes.Circle(radius=2.0)

try:
    circle.radius = 3.0  # type: ignore  # checkers reject this too
except dataclasses.FrozenInstanceError:
    pass
else:
    raise AssertionError("a variant value was changed")
```

Fields can have defaults, as in any dataclass. Don't apply `@dataclass` yourself, declare `__slots__`, or pass dataclass options: every variant is the same kind of dataclass, and superenums rejects a declaration that tries to change that. Variants are not ordered (`<`), because an order across variants needs a policy most enums don't want.

**Use keywords when fields share a type.** For a variant with fields `customer: int` and `teller: int`, `Events.ServiceStarted(teller, customer)` type-checks just as well as `Events.ServiceStarted(customer, teller)`. Write `Events.ServiceStarted(customer=c, teller=t)`, in patterns (`case Events.ServiceStarted(customer=c, teller=t):`) as well as in construction. Positional fields are safe when no two share a type, or when the order is obvious from the variant itself, as with `Shapes.Rect(w, h)`.

## Unit variants

A variant with no fields is a unit variant. It has exactly one value: calling it always returns the same cached instance, and copying or pickling that value gives the same instance back.

```python
import copy
from typing import assert_never

from superenums import Variant, Variants


class Lights(Variants):
    class Off(Variant): ...

    class On(Variant):
        brightness: int


type Light = Lights.Off | Lights.On
Lights.seal(Light)

assert Lights.Off() is Lights.Off()
assert copy.deepcopy(Lights.Off()) is Lights.Off()


def is_lit(light: Light) -> bool:
    match light:
        case Lights.Off():  # the parentheses are required
            return False
        case Lights.On(brightness=b):
            return b > 0
        case _:
            assert_never(light)


assert not is_lit(Lights.Off())
assert is_lit(Lights.On(brightness=5))
```

> [!WARNING]
> **Unit-variant patterns need parentheses.** Write `case Lights.Off():`, never `case Lights.Off:`. Without parentheses, Python reads the pattern as a *value* pattern, which compares the subject with the class `Lights.Off` itself. No value is equal to the class, so the arm never matches. A type checker reports the `match` as non-exhaustive at the `assert_never` arm. In unchecked code the value falls through to that arm and raises at runtime:
>
> <!-- expect-type-errors -->
> ```python
> from typing import assert_never
>
> from superenums import Variant, Variants
>
>
> class Lights(Variants):
>     class Off(Variant): ...
>
>     class On(Variant):
>         brightness: int
>
>
> type Light = Lights.Off | Lights.On
> Lights.seal(Light)
>
>
> def is_lit(light: Light) -> bool:
>     match light:
>         case Lights.Off:  # wrong: compares with the class, never matches
>             return False
>         case Lights.On(brightness=b):
>             return b > 0
>         case _:
>             assert_never(light)  # checkers report this line
>
>
> try:
>     is_lit(Lights.Off())
> except AssertionError:
>     pass  # Lights.Off() fell through to the assert_never arm
> else:
>     raise AssertionError("the pattern without parentheses matched")
> ```

The same goes for construction: `Lights.Off()` is the value, `Lights.Off` is the class. Rust writes `Light::Off` with no call, but no Python type checker narrows a match on a plain object like that, so superenums can't offer it without losing exhaustiveness ([why](system-design/README.md#a-unit-variant-is-a-class-with-one-cached-instance)).

A variant whose fields all have defaults is not a unit variant: `Box()` and `Box(side=2.0)` are different values, so it is never cached.

## Generic enums

An enum is generic when its variants are. Put the type parameters on each variant that uses them, with PEP 695 syntax, and on the alias. Never put them on the namespace: it is never instantiated, so its type parameters would reach nothing ([why](system-design/README.md#generic-enums-type-parameters-on-the-variants)).

```python
from typing import assert_never

from superenums import Variant, Variants


class Fetches(Variants):
    class Loaded[T](Variant):
        value: T

    class Failed(Variant):
        reason: str

    class Pending(Variant): ...


type Fetch[T] = Fetches.Loaded[T] | Fetches.Failed | Fetches.Pending
Fetches.seal(Fetch)


def value_or[T](fetch: Fetch[T], default: T) -> T:
    match fetch:
        case Fetches.Loaded(value=v):  # v: T
            return v
        case Fetches.Failed() | Fetches.Pending():
            return default
        case _:
            assert_never(fetch)


assert value_or(Fetches.Loaded(3), 0) == 3
assert value_or(Fetches.Failed("timeout"), 0) == 0
assert value_or(Fetches.Pending(), "none") == "none"
```

Variants whose fields don't depend on a type parameter stay non-generic: `Fetches.Failed` and `Fetches.Pending` fit every `Fetch[T]`, as Rust's `None` fits every `Option<T>`. Use the same parameter names across an enum's variants so the alias reads naturally. `seal` compares variant classes, not type arguments, so `Fetches.Loaded[T]` in the alias counts as `Fetches.Loaded`. Checking type arguments is the type checker's job.

## Recursive enums

A variant can hold values of its own enum. The alias is defined after the namespace, so refer to it with a quoted annotation:

```python
from typing import assert_never

from superenums import Variant, Variants


class Exprs(Variants):
    class Num(Variant):
        value: float

    class Add(Variant):
        left: "Expr"
        right: "Expr"

    class Neg(Variant):
        operand: "Expr"


type Expr = Exprs.Num | Exprs.Add | Exprs.Neg
Exprs.seal(Expr)


def evaluate(e: Expr) -> float:
    match e:
        case Exprs.Num(value):
            return value
        case Exprs.Add(left, right):
            return evaluate(left) + evaluate(right)
        case Exprs.Neg(operand):
            return -evaluate(operand)
        case _:
            assert_never(e)


assert evaluate(Exprs.Add(Exprs.Num(1.0), Exprs.Neg(Exprs.Num(3.0)))) == -2.0
```

Generic and recursive combine. Each recursive field names the alias with its type parameters:

```python
from typing import assert_never

from superenums import Variant, Variants


class Trees(Variants):
    class Leaf[T](Variant):
        value: T

    class Node[T](Variant):
        left: "Tree[T]"
        right: "Tree[T]"

    class Empty(Variant): ...


type Tree[T] = Trees.Leaf[T] | Trees.Node[T] | Trees.Empty
Trees.seal(Tree)


def leaves[T](tree: Tree[T]) -> list[T]:
    match tree:
        case Trees.Leaf(value=v):
            return [v]
        case Trees.Node(left=left, right=right):
            return leaves(left) + leaves(right)
        case Trees.Empty():
            return []
        case _:
            assert_never(tree)


tree: Tree[int] = Trees.Node(Trees.Leaf(1), Trees.Node(Trees.Empty(), Trees.Leaf(2)))
assert leaves(tree) == [1, 2]
```

## When no variant carries data, use a stdlib enum

superenums is for enums whose variants carry data. If none of them do, use a stdlib enum (`enum.Enum`) instead. Its members need no parentheses, checkers narrow them with no alias or `seal`, and it comes with iteration, names, values, and support in every serializer.

The two work well together: a stdlib enum makes a good field type.

```python
import enum
from typing import assert_never

from superenums import Variant, Variants


class Color(enum.Enum):  # no data per value: a stdlib enum
    RED = enum.auto()
    GREEN = enum.auto()


class Strokes(Variants):  # data per variant: superenums
    class Pen(Variant):
        color: Color
        width: float

    class Eraser(Variant):
        width: float


type Stroke = Strokes.Pen | Strokes.Eraser
Strokes.seal(Stroke)


def label(stroke: Stroke) -> str:
    match stroke:
        case Strokes.Pen(color=Color.RED, width=w):
            return f"red pen, {w}px"
        case Strokes.Pen(color=c, width=w):
            return f"{c.name.lower()} pen, {w}px"
        case Strokes.Eraser(width=w):
            return f"eraser, {w}px"
        case _:
            assert_never(stroke)


assert label(Strokes.Pen(Color.GREEN, 2.0)) == "green pen, 2.0px"
assert label(Strokes.Eraser(8.0)) == "eraser, 8.0px"
```

An enum made only of unit variants is still allowed, so removing the last variant with data doesn't force a rewrite. If an enum stays that way, consider switching it to a stdlib enum.

## Introspection

Four functions describe an enum at runtime. They are what extensions such as serializers build on. They are functions rather than attributes on the namespace, so they never clash with a variant's name.

- `variants(namespace)`: the namespace's variants, in declaration order.
- `alias(namespace)`: the sealed enum's union alias. It raises `SuperEnumError` before `seal`.
- `namespace_of(variant)`: the namespace a variant class or value belongs to.
- `variant_name(variant)`: a variant's plain class name (`"Circle"`), for a class or a value. It is the natural tag when serializing.

A variant's fields are the standard `dataclasses.fields`, since every variant is a dataclass.

```python
import dataclasses

from superenums import Variant, Variants, alias, namespace_of, variant_name, variants


class Shapes(Variants):
    class Circle(Variant):
        radius: float

    class Rect(Variant):
        w: float
        h: float


type Shape = Shapes.Circle | Shapes.Rect
Shapes.seal(Shape)

assert variants(Shapes) == (Shapes.Circle, Shapes.Rect)
assert alias(Shapes) is Shape
assert namespace_of(Shapes.Circle(radius=1.0)) is Shapes
assert variant_name(Shapes.Rect) == "Rect"


def to_dict(s: Shape) -> dict[str, object]:
    return {"type": variant_name(s), **dataclasses.asdict(s)}


assert to_dict(Shapes.Rect(2.0, 3.0)) == {"type": "Rect", "w": 2.0, "h": 3.0}
```

## Type checkers

superenums works with pyright, mypy, and ty, with no plugin. Every example in this guide type-checks cleanly in all three, in strict mode, apart from the parentheses trap, where each reports the `assert_never` arm as intended.

ty is still pre-1.0, and a few of its inferences differ from pyright's and mypy's. None of them affect exhaustiveness:

- In later `case` arms, ty narrows the subject to an intersection such as `Rect & ~Circle` rather than plain `Rect`. Field access and exhaustiveness are unaffected. Only an exact `assert_type` on the subject differs.
- For generic variants, ty infers the literal type argument from construction (`Fetches.Loaded(3)` is `Loaded[Literal[3]]`, not `Loaded[int]`), and a field bound in a class pattern may come out as `T | Unknown`. Annotate the value (`f: Fetch[int] = ...`) where the exact type matters.
