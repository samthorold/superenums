# superenums

Rust-style enums for Python: closed types whose values are exactly one of a fixed set of variants, each carrying its own named data.

## Language

**Enum**:
A closed type whose every value is exactly one of a fixed set of **Variants**. In this project a bare "enum" always means a superenums enum.
_Avoid_: sum type, ADT, tagged union, discriminated union (as names for our concept)

**Alias**:
The `type` statement that defines an **Enum** by listing its **Variants** (`type Shape = Circle | Rect | Empty`). The alias is the enum: it is the type used in annotations.
_Avoid_: union type, enum class

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
Describes an **Enum** whose set of **Variants** is fixed at declaration and cannot be extended afterwards. Every enum is sealed by its **Alias**: the checker sees only the variants it lists.
_Avoid_: closed, final

## Relationships

- An **Enum** is defined by one **Alias**, which lists its one or more **Variants**.
- A **Variant** is normally listed in one **Enum**. Listing it in more than one is possible but not recommended.
- An enum's **Variants** and the functions over it live in one module, which serves as their namespace (`shapes.Circle`, `shapes.area`).
- A **Variant** has zero or more **Fields**. One with zero is a **Unit variant**.
- Every **Enum** is **Sealed**.

## Flagged ambiguities

- "enum" collides with the **stdlib enum**. Resolution: "enum" alone means ours; the stdlib one is always qualified.
- "the `shapes` enum" is tempting but wrong. `shapes` is the module the **Enum** lives in; `Shape`, the **Alias**, is the **Enum**.
- "member" means a constant in the **stdlib enum**. It is never used for a **Variant** or a **Field**.

## Example dialogue

> **Dev:** Is `shapes.Empty` a member of the `Shape` enum?
> **Expert:** `Empty` is a **unit variant** of the `Shape` **enum**. "Member" is the **stdlib enum**'s word, for its constants.
> **Dev:** And in `shapes.Circle(radius=1.0)`, is the radius its payload?
> **Expert:** It's a **field** of the `Circle` **variant**. Fields always have names, even if you write `shapes.Circle(1.0)` or `case shapes.Circle(r):`.
> **Dev:** So my function parameter is annotated with a base class all the variants share?
> **Expert:** Annotate it `Shape`, the **alias**. That's the type the checker can prove an **exhaustive match** over. Variants share no base class beyond `Variant`.
> **Dev:** Can a plugin add a `Triangle` variant to `Shape`?
> **Expert:** No. Every enum is **sealed**, so the variant set is fixed where it's declared. That's what makes an **exhaustive match** provable.
