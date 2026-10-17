"""The README's Python examples run as written."""

import re
from pathlib import Path

import pytest

README = Path(__file__).resolve().parent.parent / "README.md"
EXAMPLES = re.findall(r"^```python\n(.*?)^```", README.read_text(), re.M | re.S)


def test_the_readme_has_examples() -> None:
    assert EXAMPLES


@pytest.mark.parametrize("source", EXAMPLES)
def test_readme_example_runs(source: str) -> None:
    exec(compile(source, str(README), "exec"), {"__name__": "readme"})
