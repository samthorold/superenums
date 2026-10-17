"""The documentation's Python examples run as written.

Every ```python block in the README and the user guide is executed on its own,
as a fresh module, so each block must be self-contained. Every ``match`` in
them must end in the standard ``case _: assert_never(subject)`` arm.
"""

import ast
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = [ROOT / "README.md", ROOT / "docs" / "guide.md"]


# A fence at the start of a line, or inside a blockquote (``> ```python``).
FENCE = re.compile(r"^((?:> ?)*)```python\n(.*?)^\1```", re.M | re.S)


def _examples(doc: Path) -> list[str]:
    examples: list[str] = []
    for quote, body in FENCE.findall(doc.read_text()):
        prefix = quote.rstrip()
        lines = body.splitlines(keepends=True)
        examples.append("".join(_unquote(line, quote, prefix) for line in lines))
    return examples


def _unquote(line: str, quote: str, prefix: str) -> str:
    """Strip a blockquote's ``> `` (or a bare ``>`` on an empty line)."""
    if quote and line.startswith(quote):
        return line[len(quote) :]
    if prefix and line.startswith(prefix):
        return line[len(prefix) :]
    return line


EXAMPLES = [
    pytest.param(doc, source, id=f"{doc.name}-{i}")
    for doc in DOCS
    for i, source in enumerate(_examples(doc), 1)
]


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_the_doc_has_examples(doc: Path) -> None:
    assert _examples(doc)


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_every_python_block_is_an_example(doc: Path) -> None:
    # including blocks nested in a blockquote (a callout)
    assert len(_examples(doc)) == doc.read_text().count("```python")


@pytest.mark.parametrize(("doc", "source"), EXAMPLES)
def test_example_runs(doc: Path, source: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # A fresh module registered in sys.modules, as the user's own code would
    # be: dataclass resolves a variant's quoted annotations through it.
    module = types.ModuleType("docs_example")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(source, str(doc), "exec"), module.__dict__)


def _ends_in_assert_never(match: ast.Match) -> bool:
    last = match.cases[-1]
    return (
        isinstance(last.pattern, ast.MatchAs)
        and last.pattern.pattern is None
        and last.pattern.name is None
        and last.guard is None
        and ast.unparse(last.body[-1]) == f"assert_never({ast.unparse(match.subject)})"
    )


@pytest.mark.parametrize(("doc", "source"), EXAMPLES)
def test_every_match_ends_in_assert_never(doc: Path, source: str) -> None:
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Match):
            assert _ends_in_assert_never(node), ast.unparse(node)
