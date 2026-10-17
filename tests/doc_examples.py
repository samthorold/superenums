"""The documentation's Python examples, as checked by the test suite.

Shared by the runtime check (``tests/test_docs.py``, which executes every
example) and the type-level check (``tests/typing/run.py``, which type-checks
every example). Both see exactly the same blocks.

An example is a ```python block in the README or the user guide, including
blocks inside a blockquote (a callout). An example that deliberately shows
wrong code is preceded by the invisible marker ``<!-- expect-type-errors -->``
(on its own line, inside the blockquote if the block is in one): the type-level
check requires such an example to produce errors instead of none.

An example preceded by ``<!-- module: name -->`` is a module with that name,
which later examples in the same doc can import (``import shapes``). Marker
lines can be combined, one per line, directly above the block.
"""

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = [ROOT / "README.md", ROOT / "docs" / "guide.md"]

EXPECT_TYPE_ERRORS = "<!-- expect-type-errors -->"
MODULE = re.compile(r"^<!-- module: (\w+) -->$")

# A fence at the start of a line, or inside a blockquote (``> ```python``).
FENCE = re.compile(r"^((?:> ?)*)```python\n(.*?)^\1```", re.M | re.S)


@dataclass(frozen=True)
class Example:
    doc: Path
    number: int  # 1-based position among the doc's examples
    source: str
    expects_type_errors: bool
    module: str | None  # set by a module marker: importable by later examples

    @property
    def name(self) -> str:
        """An identifier for the example, usable as a module name."""
        if self.module:
            return self.module
        stem = re.sub(r"\W", "_", self.doc.stem.lower())
        return f"{stem}_{self.number}"


def examples(doc: Path) -> list[Example]:
    text = doc.read_text()
    found: list[Example] = []
    for number, match in enumerate(FENCE.finditer(text), 1):
        quote, body = match.group(1), match.group(2)
        prefix = quote.rstrip()
        lines = body.splitlines(keepends=True)
        source = "".join(_unquote(line, quote, prefix) for line in lines)
        markers = _markers(text, match.start())
        modules = [m[1] for line in markers if (m := MODULE.match(line))]
        found.append(
            Example(
                doc,
                number,
                source,
                expects_type_errors=EXPECT_TYPE_ERRORS in markers,
                module=modules[0] if modules else None,
            )
        )
    return found


def all_examples() -> list[Example]:
    return [example for doc in DOCS for example in examples(doc)]


def _unquote(line: str, quote: str, prefix: str) -> str:
    """Strip a blockquote's ``> `` (or a bare ``>`` on an empty line)."""
    if quote and line.startswith(quote):
        return line[len(quote) :]
    if prefix and line.startswith(prefix):
        return line[len(prefix) :]
    return line


def _markers(text: str, position: int) -> list[str]:
    """The marker comments directly above ``position``, without blockquote
    markers: the consecutive ``<!-- ... -->`` lines before the block, after
    skipping blank lines."""
    markers: list[str] = []
    for line in reversed(text[:position].splitlines()):
        stripped = line.lstrip("> ").strip()
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            markers.append(stripped)
        elif stripped or markers:
            break
    return markers
