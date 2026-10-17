"""The documentation's Python examples run as written.

Every ```python block in the README and the user guide (see ``doc_examples``)
is executed on its own, as a fresh module, so each block must be
self-contained, apart from importing a module an earlier block in the same doc
defines (``<!-- module: name -->``). Every ``match`` in them must end in the
standard ``case _: assert_never(subject)`` arm.
"""

import ast
import sys
import types
from pathlib import Path

import pytest
from doc_examples import (
    DOCS,
    EXPECT_TYPE_ERRORS,
    MODULE,
    Example,
    all_examples,
    examples,
)

EXAMPLES = [pytest.param(example, id=example.name) for example in all_examples()]


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_the_doc_has_examples(doc: Path) -> None:
    assert examples(doc)


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_every_python_block_is_an_example(doc: Path) -> None:
    # including blocks nested in a blockquote (a callout)
    assert len(examples(doc)) == doc.read_text().count("```python")


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_every_type_error_marker_precedes_an_example(doc: Path) -> None:
    marked = [example for example in examples(doc) if example.expects_type_errors]
    assert len(marked) == doc.read_text().count(EXPECT_TYPE_ERRORS)


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_every_module_marker_precedes_an_example(doc: Path) -> None:
    named = [example for example in examples(doc) if example.module]
    markers = [
        line
        for line in doc.read_text().splitlines()
        if MODULE.match(line.lstrip("> ").strip())
    ]
    assert len(named) == len(markers)


def test_module_names_are_unique_across_the_docs() -> None:
    # The type-level check writes every example to one directory.
    names = [example.name for example in all_examples()]
    assert len(names) == len(set(names))


def _run(example: Example, monkeypatch: pytest.MonkeyPatch) -> None:
    # A fresh module registered in sys.modules, as the user's own code would
    # be: dataclass resolves a variant's quoted annotations through it.
    module = types.ModuleType(example.module or "docs_example")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(example.source, str(example.doc), "exec"), module.__dict__)


@pytest.mark.parametrize("example", EXAMPLES)
def test_example_runs(example: Example, monkeypatch: pytest.MonkeyPatch) -> None:
    # The modules it may import: those defined earlier in the same doc.
    for earlier in examples(example.doc)[: example.number - 1]:
        if earlier.module:
            _run(earlier, monkeypatch)
    _run(example, monkeypatch)


def _ends_in_assert_never(match: ast.Match) -> bool:
    last = match.cases[-1]
    return (
        isinstance(last.pattern, ast.MatchAs)
        and last.pattern.pattern is None
        and last.pattern.name is None
        and last.guard is None
        and ast.unparse(last.body[-1]) == f"assert_never({ast.unparse(match.subject)})"
    )


@pytest.mark.parametrize("example", EXAMPLES)
def test_every_match_ends_in_assert_never(example: Example) -> None:
    for node in ast.walk(ast.parse(example.source)):
        if isinstance(node, ast.Match):
            assert _ends_in_assert_never(node), ast.unparse(node)
