# The superenums guide

This guide shows how to write enums with superenums, the way the library is designed to be used. Every example here runs as part of the test suite.

The words used throughout:

- **enum**: a closed type whose values are exactly one of a fixed set of variants. Here, always a superenums enum, written as a union alias (`Shape`).
- **variant**: one alternative of an enum (`Circle`). A **unit variant** has no fields.
- **field**: a named, typed piece of data on a variant (`radius`).
- **sealed**: every enum's set of variants is fixed where its alias is written.
- **stdlib enum**: Python's own `enum.Enum`, always called that, never a bare "enum".

The reasons behind the design are in [the system design](system-design/README.md). This guide links there rather than repeating them.

## Declaring an enum

An enum is a set of variant classes and a `type` alias that lists them. Give each enum its own module, named after it. Here is `shapes.py`:

<!-- module: shapes -->
```python
from typing import assert_never

from superenums import Variant


class Circle(Variant):
    radius: float


class Rect(Variant):
    w: float
    h: float


class Empty(Variant): ...  # a unit variant: no fields


type Shape = Circle | Rect | Empty  # the enum


def area(s: Shape) -> float:
    match s:
        case Circle(radius=r):
            return 3.14159 * r * r
        case Rect(w, h):
            return w * h
        case Empty():
            return 0.0
        case _:
            assert_never(s)
```

- **A variant** is a class that subclasses `Variant`. Its annotations are its fields.
- **The alias** is a `type` statement listing every variant. It is the enum: the type you annotate with, and the only place the variants are listed. A type checker can prove a `match` exhaustive only over a union like this one ([why](system-design/README.md#an-enum-is-its-union-alias)).
- **The functions** over the enum live in the same module.

Other code imports the module, which acts as the enum's namespace:

```python
from typing import assert_never

import shapes

circle = shapes.Circle(radius=1.0)
rect = shapes.Rect(2.0, 3.0)  # fields can be given positionally, in order
assert shapes.area(rect) == 6.0


def is_round(s: shapes.Shape) -> bool:
    match s:
        case shapes.Circle():
            return True
        case shapes.Rect() | shapes.Empty():
            return False
        case _:
            assert_never(s)


assert is_round(circle)
```

`shapes.Circle` reads like Rust's `Shape::Circle`, and `shapes.area` like a method in its `impl` block. Code that uses an enum heavily can import the names it needs instead (`from shapes import Circle, Shape`).

Nothing else is needed: no registration, no base class for the enum. A variant you forget to list in the alias is reported by the type checker wherever you use it as the enum, such as passing it where a `Shape` is expected.

### Naming: one module per enum

Name the enum in the singular (`Shape`: one value is a shape), and its module after it (`shapes`). Two enums in one module can't both have a variant called `Empty`, which is the main reason for one module per enum. If two small enums must share a module, give the variants names that say which enum they belong to (`EmptyShape`, `EmptyPath`).

Don't group variants in a plain class to get `Shapes.Circle` inside one module. It works, but the class is a name you can annotate with by mistake, which silently defeats exhaustiveness ([below](#annotate-with-the-alias)).

`SuperEnumError` is a `TypeError`. superenums raises it for every declaration or use it doesn't allow, such as subclassing a variant, or applying `@dataclass` to one.

## Behaviour is a free function with one `match`

Behaviour over an enum is an ordinary function that takes the enum and contains one `match`, written in the enum's module. It is the Python form of a Rust `impl` block whose method matches on `self`.

```python
from typing import assert_never

from superenums import Variant


class Circle(Variant):
    radius: float


class Rect(Variant):
    w: float
    h: float


class Empty(Variant): ...


type Shape = Circle | Rect | Empty


def describe(s: Shape) -> str:
    match s:
        case Circle(radius=r) if r > 10:  # guards work as usual
            return "a big circle"
        case Circle():
            return "a circle"
        case Rect(w, h) if w == h:
            return "a square"
        case Rect():
            return "a rectangle"
        case Empty():
            return "nothing"
        case _:
            assert_never(s)


assert describe(Rect(2.0, 2.0)) == "a square"
assert describe(Circle(radius=20.0)) == "a big circle"
```

Inside each arm the checker narrows `s` to that variant, so its fields are typed: `r` is a `float`. Add a variant to the alias, and every function like this fails to type-check until it handles the new variant.

### When it has to be a method

Some behaviour has to be a method, because Python looks for it on the value's class: operators, `str()`, `len()`, iteration, or a method a `Protocol` requires. Write the method on each variant. Calling it on the enum type-checks only if every variant defines it, so a variant without it is reported wherever the method is called on the enum:

```python
from superenums import Variant


class Circle(Variant):
    radius: float

    def area(self) -> float:
        return 3.14159 * self.radius * self.radius


class Rect(Variant):
    w: float
    h: float

    def area(self) -> float:
        return self.w * self.h


type Shape = Circle | Rect


def total_area(shapes: list[Shape]) -> float:
    return sum(s.area() for s in shapes)


assert total_area([Rect(2.0, 3.0), Rect(1.0, 1.0)]) == 7.0
```

Prefer the free function for everything else: it keeps the whole behaviour in one place, and superenums has no machinery for methods on an enum ([why](system-design/README.md#behaviour-over-an-enum-is-a-free-function)).

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

### Annotate with the alias

> [!IMPORTANT]
> **Annotate with the enum's alias, never with a class.** Write `def area(s: Shape)`. A class can always gain subclasses, so no `match` over a value annotated with a class is proven exhaustive, even one that handles every variant. That includes a base class you share between the variants and a class you group them in. Every checker reports the `assert_never` arm, so the mistake shows up as an error there, not silently, but the fix is always the same: annotate with the alias.

The same holds wherever an enum appears in a type: `list[Shape]`, `dict[str, Shape]`, `Shape | None`, a field typed with another enum.

### Handling only some variants

A function often cares about only a few variants: a logger that reports only errors, or a process in a simulation that reacts only to arrivals. There are two ways to write the rest, and which one you use is a deliberate choice.

**List the rest in an ignore arm**, then end with the standard `assert_never` arm:

```python
from typing import assert_never

from superenums import Variant


class Arrived(Variant):
    customer: int


class ServiceStarted(Variant):
    customer: int


class ServiceFinished(Variant):
    customer: int


class DoorsClosed(Variant): ...


type Event = Arrived | ServiceStarted | ServiceFinished | DoorsClosed


def queue_length(events: list[Event]) -> int:
    waiting = 0
    for event in events:
        match event:
            case Arrived():
                waiting += 1
            case ServiceStarted():
                waiting -= 1
            case ServiceFinished() | DoorsClosed():
                pass  # no effect on the queue
            case _:
                assert_never(event)
    return waiting


assert queue_length([Arrived(1), Arrived(2), ServiceStarted(1)]) == 1
```

Add a variant and this `match` fails to type-check until the new variant is put in an arm, even if that arm is the ignore arm. Each such function makes its own decision about the new variant. Use this form when the function is only correct if it sees every variant that matters to it. Here, a new `CustomerLeftQueue` variant has to reduce the count.

**Or end with `case _: pass`** (or `case _: return None`, or whatever "not interested" means in that function) in place of the `assert_never` arm. A new variant then falls into the wildcard, and no checker reports it. Use this form when the function stays correct whatever variants are added, such as a filter that picks out one variant.

Neither form is a loophole. The wildcard form opts that one `match` out of exhaustiveness checking, and it's visible in the code. What superenums guarantees is that the explicit form is checked, not that every `match` uses it. The examples in this guide all use the standard arm.

### Matching two enums at once

A state machine's step takes a state and an event, both enums. Nest one `match` inside the other, so each enum gets its own exhaustive match:

```python
from typing import assert_never

from superenums import Variant


class Idle(Variant): ...


class Busy(Variant):
    job: int


type State = Idle | Busy


class Start(Variant):
    job: int


class Finish(Variant): ...


type Event = Start | Finish


def step(state: State, event: Event) -> State:
    match state:
        case Idle():
            match event:
                case Start(job=j):
                    return Busy(j)
                case Finish():
                    return state
                case _:
                    assert_never(event)
        case Busy():
            match event:
                case Start():
                    return state  # busy: ignore new work
                case Finish():
                    return Idle()
                case _:
                    assert_never(event)
        case _:
            assert_never(state)


assert step(step(Idle(), Start(job=1)), Finish()) is Idle()
```

Matching on a tuple (`match (state, event):` with arms like `case (Idle(), Start(job=j)):`) reads more like a transition table. pyright and ty prove it exhaustive, and pyright names a missing combination. mypy doesn't narrow a tuple of unions, so it reports even a complete tuple match. Use the nested form if your code is checked with mypy.

## Data shared by every variant

When every variant carries the same data, such as an event's timestamp, don't add it to each variant or give them a base class with the field. Keep the enum for what differs between the variants, and wrap it in a type that holds the shared data, as Rust code does with `struct Event { t, kind }`:

```python
from dataclasses import dataclass
from typing import assert_never

from superenums import Variant


class Arrived(Variant):
    customer: int


class DoorsClosed(Variant): ...


type BankEvent = Arrived | DoorsClosed


@dataclass(frozen=True)
class Timed[E]:
    t: float  # shared by every event
    event: E


def log_line(timed: Timed[BankEvent]) -> str:
    match timed.event:
        case Arrived(customer=c):
            return f"{timed.t}: customer {c} arrives"
        case DoorsClosed():
            return f"{timed.t}: doors close"
        case _:
            assert_never(timed.event)


assert log_line(Timed(9.5, Arrived(customer=1))) == "9.5: customer 1 arrives"
```

A base class with the shared field would save repeating it, but it isn't the enum: annotating with it defeats exhaustiveness ([above](#annotate-with-the-alias)), and variants can't inherit from one another anyway ([why](system-design/README.md#shared-data-goes-in-a-wrapper-not-a-base-class)). A field only some variants share is declared on each of them, as in Rust.

## Variant values

A variant is a frozen, slotted dataclass. Its values are immutable, compare and hash by variant and field values, and have a readable `repr`. To change a value, make a new one with `dataclasses.replace`.

```python
import dataclasses

from superenums import Variant


class Circle(Variant):
    radius: float


class Square(Variant):
    side: float


type Shape = Circle | Square

circle = Circle(radius=1.0)
assert circle == Circle(1.0)
assert repr(circle) == "Circle(radius=1.0)"
# different variants never compare equal, even with identical fields
assert len({circle, Circle(1.0), Square(1.0)}) == 2

bigger = dataclasses.replace(circle, radius=2.0)
assert bigger == Circle(radius=2.0)

try:
    circle.radius = 3.0  # type: ignore  # checkers reject this too
except dataclasses.FrozenInstanceError:
    pass
else:
    raise AssertionError("a variant value was changed")
```

Fields can have defaults, as in any dataclass. Don't apply `@dataclass` yourself, declare `__slots__`, or pass dataclass options: every variant is the same kind of dataclass, and superenums rejects a declaration that tries to change that. Variants are not ordered (`<`), because an order across variants needs a policy most enums don't want.

### Keyword-only fields

When two fields share a type, positional arguments are easy to swap without anyone noticing. For a variant with fields `customer: int` and `teller: int`, `ServiceStarted(teller, customer)` type-checks just as well as `ServiceStarted(customer, teller)`. Make such fields keyword-only with the standard `dataclasses.KW_ONLY` marker: every field after it must be given by name, both when constructing and in patterns.

```python
from dataclasses import KW_ONLY
from typing import assert_never

from superenums import Variant


class ServiceStarted(Variant):
    _: KW_ONLY
    customer: int
    teller: int


class Note(Variant):
    text: str  # positional, before the marker
    _: KW_ONLY
    customer: int


type Event = ServiceStarted | Note

started = ServiceStarted(customer=1, teller=2)
note = Note("asked about a loan", customer=1)


def customer(event: Event) -> int:
    match event:
        case ServiceStarted(customer=c):
            return c
        case Note(_, customer=c):
            return c
        case _:
            assert_never(event)


assert customer(started) == customer(note) == 1

try:
    ServiceStarted(1, 2)  # type: ignore  # checkers reject this too
except TypeError:
    pass
else:
    raise AssertionError("keyword-only fields were given positionally")
```

pyright, mypy and ty all report a positional argument or a positional sub-pattern for a keyword-only field. The marker is a dataclass feature, not an option to superenums: `_` is not a field, and `dataclasses.fields` doesn't list it. Use it whenever fields share a type. Positional fields are safe when no two share a type, or when the order is obvious from the variant itself, as with `Rect(w, h)`.

## Unit variants

A variant with no fields is a unit variant. It has exactly one value: calling it always returns the same cached instance, and copying or pickling that value gives the same instance back. Here is `lights.py`:

<!-- module: lights -->
```python
import copy
from typing import assert_never

from superenums import Variant


class Off(Variant): ...


class On(Variant):
    brightness: int


type Light = Off | On

assert Off() is Off()
assert copy.deepcopy(Off()) is Off()


def is_lit(light: Light) -> bool:
    match light:
        case Off():  # the parentheses are required
            return False
        case On(brightness=b):
            return b > 0
        case _:
            assert_never(light)


assert not is_lit(Off())
assert is_lit(On(brightness=5))
```

> [!WARNING]
> **Unit-variant patterns need parentheses.** Write `case lights.Off():`, never `case lights.Off:`. Without parentheses, Python reads a dotted name as a *value* pattern, which compares the subject with the class `lights.Off` itself. No value is equal to the class, so the arm never matches. A type checker reports the `match` as non-exhaustive at the `assert_never` arm. In unchecked code the value falls through to that arm and raises at runtime:
>
> <!-- expect-type-errors -->
> ```python
> from typing import assert_never
>
> import lights
>
>
> def is_lit(light: lights.Light) -> bool:
>     match light:
>         case lights.Off:  # wrong: compares with the class, never matches
>             return False
>         case lights.On(brightness=b):
>             return b > 0
>         case _:
>             assert_never(light)  # checkers report this line
>
>
> try:
>     is_lit(lights.Off())
> except AssertionError:
>     pass  # lights.Off() fell through to the assert_never arm
> else:
>     raise AssertionError("the pattern without parentheses matched")
> ```
>
> A bare name without parentheses (`case Off:`) is worse: it is a *capture* pattern, which matches anything and binds the value to the name `Off`. Python refuses to compile one before the last arm, but as the last arm it silently catches every remaining value.

The same goes for construction: `Off()` is the value, `Off` is the class. Rust writes `Light::Off` with no call, but no Python type checker narrows a match on a plain object like that, so superenums can't offer it without losing exhaustiveness ([why](system-design/README.md#a-unit-variant-is-a-class-with-one-cached-instance)).

A variant whose fields all have defaults is not a unit variant: `Box()` and `Box(side=2.0)` are different values, so it is never cached.

## Generic enums

An enum is generic when its variants are. Put the type parameters on each variant that uses them, with PEP 695 syntax, and on the alias ([why](system-design/README.md#generic-enums-type-parameters-on-the-variants)).

```python
from typing import assert_never

from superenums import Variant


class Loaded[T](Variant):
    value: T


class Failed(Variant):
    reason: str


class Pending(Variant): ...


type Fetch[T] = Loaded[T] | Failed | Pending


def value_or[T](fetch: Fetch[T], default: T) -> T:
    match fetch:
        case Loaded(value=v):  # v: T
            return v
        case Failed() | Pending():
            return default
        case _:
            assert_never(fetch)


assert value_or(Loaded(3), 0) == 3
assert value_or(Failed("timeout"), 0) == 0
assert value_or(Pending(), "none") == "none"
```

Variants whose fields don't depend on a type parameter stay non-generic: `Failed` and `Pending` fit every `Fetch[T]`, as Rust's `None` fits every `Option<T>`. Use the same parameter names across an enum's variants so the alias reads naturally.

## Recursive enums

A variant can hold values of its own enum. The alias is defined after the variants, so refer to it with a quoted annotation:

```python
from typing import assert_never

from superenums import Variant


class Num(Variant):
    value: float


class Add(Variant):
    left: "Expr"
    right: "Expr"


class Neg(Variant):
    operand: "Expr"


type Expr = Num | Add | Neg


def evaluate(e: Expr) -> float:
    match e:
        case Num(value):
            return value
        case Add(left, right):
            return evaluate(left) + evaluate(right)
        case Neg(operand):
            return -evaluate(operand)
        case _:
            assert_never(e)


assert evaluate(Add(Num(1.0), Neg(Num(3.0)))) == -2.0
```

Generic and recursive combine. Each recursive field names the alias with its type parameters:

```python
from typing import assert_never

from superenums import Variant


class Leaf[T](Variant):
    value: T


class Node[T](Variant):
    left: "Tree[T]"
    right: "Tree[T]"


class Empty(Variant): ...


type Tree[T] = Leaf[T] | Node[T] | Empty


def leaves[T](tree: Tree[T]) -> list[T]:
    match tree:
        case Leaf(value=v):
            return [v]
        case Node(left=left, right=right):
            return leaves(left) + leaves(right)
        case Empty():
            return []
        case _:
            assert_never(tree)


tree: Tree[int] = Node(Leaf(1), Node(Empty(), Leaf(2)))
assert leaves(tree) == [1, 2]
```

## When no variant carries data, use a stdlib enum

superenums is for enums whose variants carry data. If none of them do, use a stdlib enum (`enum.Enum`) instead. Its members need no parentheses, checkers narrow them with no alias, and it comes with iteration, names, values, and support in every serializer.

The two work well together: a stdlib enum makes a good field type.

```python
import enum
from typing import assert_never

from superenums import Variant


class Color(enum.Enum):  # no data per value: a stdlib enum
    RED = enum.auto()
    GREEN = enum.auto()


class Pen(Variant):  # data per variant: superenums
    color: Color
    width: float


class Eraser(Variant):
    width: float


type Stroke = Pen | Eraser


def label(stroke: Stroke) -> str:
    match stroke:
        case Pen(color=Color.RED, width=w):
            return f"red pen, {w}px"
        case Pen(color=c, width=w):
            return f"{c.name.lower()} pen, {w}px"
        case Eraser(width=w):
            return f"eraser, {w}px"
        case _:
            assert_never(stroke)


assert label(Pen(Color.GREEN, 2.0)) == "green pen, 2.0px"
assert label(Eraser(8.0)) == "eraser, 8.0px"
```

An enum made only of unit variants is still allowed, so removing the last variant with data doesn't force a rewrite. If an enum stays that way, consider switching it to a stdlib enum.

## Serialization

Serialization is an extension, with one module per library. Each writes a value as an object holding its fields plus a tag naming its variant, `{"type": "Circle", "radius": 1.0}` ([why](system-design/README.md#serialization-the-tag-goes-inside-the-object)). A unit variant is just its tag, `{"type": "Empty"}`, and loading it gives back its one value.

### cattrs

Install the extra (`pip install superenums[cattrs]`, or `uv add superenums[cattrs]`), then configure a converter once per enum:

```python
from dataclasses import dataclass

import cattrs

import superenums.cattrs
from superenums import Variant


class Circle(Variant):
    radius: float


class Empty(Variant): ...


type Shape = Circle | Empty


@dataclass(frozen=True)
class Drawing:
    name: str
    shape: Shape


converter = cattrs.Converter()
superenums.cattrs.configure(Shape, converter)

drawing = Drawing("dot", Circle(1.0))
data = converter.unstructure(drawing)
assert data == {"name": "dot", "shape": {"type": "Circle", "radius": 1.0}}
assert converter.structure(data, Drawing) == drawing

# On its own, an enum value needs its alias: cattrs can't tell from the value
assert converter.unstructure(Empty(), Shape) == {"type": "Empty"}
shape: Shape = converter.structure({"type": "Empty"}, Shape.__value__)
assert shape is Empty()
```

- **Pass the alias when writing a value on its own.** `converter.unstructure(Empty())` sees only the class `Empty`, writes `{}`, and loses the tag. Fields annotated with the alias, as in `Drawing`, are tagged automatically.
- **Load with `Shape.__value__`.** cattrs types `structure`'s target as a class, so checkers reject `converter.structure(data, Shape)` (it works at runtime). The alias's value, the union it names, is accepted, and annotating the result (`shape: Shape = ...`) gives it its type back.
- **The tag key** is `"type"`. Change it with `configure(Shape, converter, key="kind")`. A variant with a field named like the key, or two variants with the same name (from different modules), is refused with `SuperEnumError` when configuring.
- **Generic enums** are configured once (`configure(Tree, converter)`) and loaded through a specialisation (`converter.structure(data, Tree[int])`), whose type arguments reach the fields. A recursive generic enum needs Python 3.12.4 or later, where `typing.get_type_hints` first sees a class's type parameters.
- Variants must unstructure to dicts, cattrs' default. A converter configured to write them as tuples is refused when writing.

### pydantic

Install the extra (`pip install superenums[pydantic]`). There is nothing to import or configure: annotate with the alias, as anywhere else.

```python
from pydantic import BaseModel, TypeAdapter

from superenums import Variant


class Circle(Variant):
    radius: float


class Empty(Variant): ...


type Shape = Circle | Empty


class Drawing(BaseModel):
    name: str
    shape: Shape


drawing = Drawing(name="dot", shape=Circle(1.0))
assert drawing.model_dump() == {
    "name": "dot",
    "shape": {"type": "Circle", "radius": 1.0},
}
assert Drawing.model_validate_json(drawing.model_dump_json()) == drawing

shapes = TypeAdapter(Shape)
assert shapes.dump_python(Empty()) == {"type": "Empty"}
assert shapes.validate_json('{"type": "Empty"}') is Empty()
```

- **The tag key is always `"type"`.** A variant with a field named `type` is refused with `SuperEnumError` when pydantic first builds a schema for it.
- **A variant used on its own is tagged too** (a field annotated `Circle`), and so are generic enums (`TypeAdapter(Tree[int])`). The JSON Schema requires the tag, as a `const`.
- **A variant in an untyped field (`Any`, `dict[str, Any]`) is written as a plain dataclass, without its tag**: pydantic only knows to tag it from the annotation.
- pydantic config on a variant (`pydantic.with_config`, or `__pydantic_config__` in the class body) is honoured.
- Validation errors list every variant, since pydantic tries each one in turn.

## Introspection

Two functions describe an enum at runtime. They are what extensions such as serializers build on.

- `variants(alias)`: the enum's variants, in the order its alias lists them. It raises `SuperEnumError` if given anything but an alias of variants. A generic variant counts as its class, whatever type arguments the alias gives it.
- `variant_name(variant)`: a variant's plain class name (`"Circle"`), for a class or a value. It is the natural tag when serializing.

A variant's fields are the standard `dataclasses.fields`, since every variant is a dataclass.

```python
import dataclasses

from superenums import Variant, variant_name, variants


class Circle(Variant):
    radius: float


class Rect(Variant):
    w: float
    h: float


type Shape = Circle | Rect

assert variants(Shape) == (Circle, Rect)
assert variant_name(Rect) == "Rect"


def to_dict(s: Shape) -> dict[str, object]:
    return {"type": variant_name(s), **dataclasses.asdict(s)}


assert to_dict(Rect(2.0, 3.0)) == {"type": "Rect", "w": 2.0, "h": 3.0}
```

## Type checkers

superenums works with pyright, mypy, and ty, with no plugin. Every example in this guide type-checks cleanly in all three, in strict mode, apart from the parentheses trap, where each reports the `assert_never` arm as intended.

ty is still pre-1.0, and a few of its inferences differ from pyright's and mypy's. None of them affect exhaustiveness:

- In later `case` arms, ty narrows the subject to an intersection such as `Rect & ~Circle` rather than plain `Rect`. Field access and exhaustiveness are unaffected. Only an exact `assert_type` on the subject differs.
- For generic variants, ty infers the literal type argument from construction (`Loaded(3)` is `Loaded[Literal[3]]`, not `Loaded[int]`), and a field bound in a class pattern may come out as `T | Unknown`. Annotate the value (`f: Fetch[int] = ...`) where the exact type matters.

mypy doesn't narrow a tuple of unions, so it can't prove a `match (a, b):` over two enums exhaustive ([Matching two enums at once](#matching-two-enums-at-once)).
