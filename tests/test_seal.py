import pytest

from superenums import SuperEnumError, Variant, Variants


def test_seal_names_each_variant_the_alias_omits() -> None:
    class Pets(Variants):
        class Cat(Variant): ...

        class Dog(Variant): ...

        class Eel(Variant): ...

    type Pet = Pets.Cat
    with pytest.raises(SuperEnumError) as excinfo:
        Pets.seal(Pet)
    message = str(excinfo.value)
    assert "Pets" in message
    assert "missing" in message
    assert "Pets.Dog" in message
    assert "Pets.Eel" in message


def test_seal_names_each_variant_the_alias_lists_but_the_namespace_lacks() -> None:
    class Birds(Variants):
        class Owl(Variant): ...

    class Pets(Variants):
        class Cat(Variant): ...

    type Pet = Pets.Cat | Birds.Owl
    with pytest.raises(SuperEnumError) as excinfo:
        Pets.seal(Pet)
    message = str(excinfo.value)
    assert "Pets" in message
    assert "extra" in message
    assert "Birds.Owl" in message
    assert "missing" not in message


def test_sealing_an_already_sealed_namespace_raises() -> None:
    class Pets(Variants):
        class Cat(Variant): ...

    type Pet = Pets.Cat
    Pets.seal(Pet)
    with pytest.raises(SuperEnumError, match=r"Pets.*already sealed"):
        Pets.seal(Pet)


def test_a_sealed_namespace_rejects_adding_replacing_or_deleting_attributes() -> None:
    class Pets(Variants):
        class Cat(Variant): ...

    type Pet = Pets.Cat
    Pets.seal(Pet)

    class Dog(Variant): ...

    with pytest.raises(SuperEnumError, match=r"Pets.*sealed"):
        Pets.Dog = Dog  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(SuperEnumError, match=r"Pets.*sealed"):
        Pets.Cat = Dog  # type: ignore[misc, assignment]  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(SuperEnumError, match=r"Pets.*sealed"):
        del Pets.Cat
    assert not hasattr(Pets, "Dog")
    assert Pets.__dict__["Cat"].__name__ == "Cat"


def test_an_unsealed_namespace_is_not_locked() -> None:
    class Pets(Variants):
        class Cat(Variant): ...

    Pets.note = "draft"  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
    assert Pets.note == "draft"  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]


def test_constructing_a_variant_of_an_unsealed_namespace_says_to_add_seal() -> None:
    class Pets(Variants):
        class Cat(Variant):
            name: str

        class Dog(Variant): ...

    with pytest.raises(SuperEnumError, match=r"Pets is not sealed.*Pets\.seal"):
        Pets.Cat("Tom")
    with pytest.raises(SuperEnumError, match=r"Pets is not sealed.*Pets\.seal"):
        Pets.Dog()

    type Pet = Pets.Cat | Pets.Dog
    Pets.seal(Pet)
    assert Pets.Cat("Tom").name == "Tom"
    assert Pets.Dog() == Pets.Dog()


def test_a_variant_declared_outside_any_namespace_cannot_be_constructed() -> None:
    class Stray(Variant):
        name: str

    with pytest.raises(SuperEnumError, match=r"Stray.*outside any namespace"):
        Stray("lost")
