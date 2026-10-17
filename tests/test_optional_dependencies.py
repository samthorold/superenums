"""The core depends on nothing: each serialization library is an extra."""

import subprocess
import sys

BLOCK_AND_IMPORT = """
import importlib.abc
import sys

class Absent(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.partition(".")[0] in {"cattrs", "pydantic", "pydantic_core", "msgspec"}:
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return None

sys.meta_path.insert(0, Absent())
import superenums

class Circle(superenums.Variant):
    radius: float

type Shape = Circle
assert superenums.variants(Shape) == (Circle,)
assert Circle(1.0).radius == 1.0
"""


def test_the_core_works_without_any_serialization_library() -> None:
    result = subprocess.run(
        [sys.executable, "-c", BLOCK_AND_IMPORT],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
