# superenums

Rust-style enums for Python: closed types whose values are exactly one of a fixed set of variants, each carrying its own named data.

## Language

**Enum**:
A closed type whose every value is exactly one of a fixed set of **Variants**. In this project a bare "enum" always means a superenums enum.
_Avoid_: sum type, ADT, tagged union, discriminated union (as names for our concept)

**Namespace**:
The class that holds an **Enum**'s **Variants**. Named in the plural (`Shapes`), while the **Enum** is singular (`Shape`). The namespace is not the enum.
_Avoid_: enum class, enum (for the namespace), container

**stdlib enum**:
Python's `enum.Enum` and its relatives: a fixed set of constant values with no per-value data. Always qualified, never a bare "enum".
_Avoid_: enum (unqualified), Python enum

**Variant**:
One alternative of an **Enum**, e.g. `Circle` in `Shape`. It has zero or more **Fields**.
_Avoid_: case, constructor, member, kind

**Unit variant**:
A **Variant** with no **Fields**. It has exactly one value.
_Avoid_: constant, singleton variant, empty variant

**Field**:
A named, typed piece of data carried by a **Variant**. Fields are always named, even when a pattern or constructor gives them positionally.
_Avoid_: payload, associated value, member, attribute

**Exhaustive match**:
A match over an **Enum** that handles every **Variant**.
_Avoid_: complete match, total match

**Sealed**:
Describes an **Enum** whose set of **Variants** is fixed at declaration and cannot be extended afterwards.
_Avoid_: closed, final

## Relationships

- An **Enum** has one or more **Variants**. A **Variant** belongs to exactly one **Enum**.
- Each **Enum** has exactly one **Namespace**, which holds its **Variants**.
- A **Variant** has zero or more **Fields**. One with zero is a **Unit variant**.
- Every **Enum** is **Sealed**.

## Flagged ambiguities

- "enum" collides with the **stdlib enum**. Resolution: "enum" alone means ours; the stdlib one is always qualified.
- "the `Shapes` enum" is tempting but wrong. `Shapes` is the **Namespace**; `Shape` is the **Enum**.
- "member" means a constant in the **stdlib enum**. It is never used for a **Variant** or a **Field**.

## Example dialogue

> **Dev:** Is `Shapes.Empty` a member of the `Shapes` enum?
> **Expert:** `Shapes` is the **namespace**, not the enum. `Empty` is a **unit variant** of the `Shape` **enum**. "Member" is the **stdlib enum**'s word, for its constants.
> **Dev:** And in `Shapes.Circle(radius=1.0)`, is the radius its payload?
> **Expert:** It's a **field** of the `Circle` **variant**. Fields always have names, even if you write `Shapes.Circle(1.0)` or `case Shapes.Circle(r):`.
> **Dev:** So my function parameter is annotated `Shapes`?
> **Expert:** Annotate it `Shape`, the **enum**. That's the type the checker can prove an **exhaustive match** over.
> **Dev:** Can a plugin add a `Triangle` variant to `Shape`?
> **Expert:** No. Every enum is **sealed**, so the variant set is fixed where it's declared. That's what makes an **exhaustive match** provable.
