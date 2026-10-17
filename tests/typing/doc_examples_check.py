"""Type-check the documentation's examples with pyright, mypy and ty.

Each example (see ``tests/doc_examples.py``) is written to its own module in a
temporary directory and checked in the configuration the guide recommends:
pyright strict with ``reportMatchNotExhaustive``, ``mypy --strict``, and ty's
defaults, all targeting Python 3.12. An ordinary example must produce no
errors. An example marked ``<!-- expect-type-errors -->`` must produce at least
one, so a deliberately wrong example stays wrong in every checker.

As in the rest of the type-level suite, pyright and mypy are required and ty is
advisory.
"""

import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from doc_examples import Example, all_examples

PYTHON_VERSION = "3.12"

# Errors per example module name: {"guide_3": ["12: message", ...]}
Errors = dict[str, list[str]]


def _pyright(directory: Path) -> Errors:
    config = {
        "typeCheckingMode": "strict",
        "reportMatchNotExhaustive": "error",
        "pythonVersion": PYTHON_VERSION,
    }
    (directory / "pyrightconfig.json").write_text(json.dumps(config))
    result = _run(
        [
            "pyright",
            "--outputjson",
            "--pythonpath",
            sys.executable,
            "-p",
            str(directory),
        ],
        directory,
    )
    errors: Errors = defaultdict(list)
    for diagnostic in json.loads(result.stdout)["generalDiagnostics"]:
        if diagnostic["severity"] == "error":
            line = diagnostic["range"]["start"]["line"] + 1
            rule = diagnostic.get("rule", "")
            errors[Path(diagnostic["file"]).stem].append(
                f"{line}: {diagnostic['message']} [{rule}]"
            )
    return errors


def _mypy(directory: Path) -> Errors:
    config = directory / "mypy.ini"
    config.write_text(f"[mypy]\nstrict = true\npython_version = {PYTHON_VERSION}\n")
    files = sorted(str(path) for path in directory.glob("*.py"))
    result = _run(
        [
            "mypy",
            "--config-file",
            str(config),
            "--cache-dir",
            str(directory / ".mypy_cache"),
            "--no-error-summary",
            *files,
        ],
        directory,
    )
    return _parse_lines(
        result.stdout, r"^(?P<file>[^:]+\.py):(?P<line>\d+): error: (?P<msg>.*)$"
    )


def _ty(directory: Path) -> Errors:
    result = _run(
        [
            "ty",
            "check",
            "--python",
            sys.prefix,
            "--python-version",
            PYTHON_VERSION,
            "--output-format",
            "concise",
            ".",
        ],
        directory,
    )
    return _parse_lines(
        result.stdout, r"^(?P<file>[^:]+\.py):(?P<line>\d+):\d+: error(?P<msg>.*)$"
    )


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def _parse_lines(output: str, pattern: str) -> Errors:
    errors: Errors = defaultdict(list)
    for match in re.finditer(pattern, output, re.M):
        errors[Path(match["file"]).stem].append(
            f"{match['line']}: {match['msg'].strip()}"
        )
    return errors


# (name, checker, fails the build)
CHECKERS: list[tuple[str, Callable[[Path], Errors], bool]] = [
    ("pyright", _pyright, True),
    ("mypy", _mypy, True),
    ("ty", _ty, False),
]


def _problems(examples: list[Example], errors: Errors) -> list[str]:
    problems: list[str] = []
    for example in examples:
        found = errors.get(example.name, [])
        where = f"{example.doc.name} example {example.number}"
        if example.expects_type_errors and not found:
            problems.append(f"{where}: marked expect-type-errors, but has no errors")
        elif not example.expects_type_errors and found:
            problems.extend(f"{where}, line {error}" for error in found)
    return problems


def main() -> int:
    """Check every example under each checker; non-zero on a required failure."""
    examples = all_examples()
    failed: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        for example in examples:
            (directory / f"{example.name}.py").write_text(example.source)
        for name, check, required in CHECKERS:
            print(f"--- {name} (doc examples) ---", flush=True)
            problems = _problems(examples, check(directory))
            for problem in problems:
                print(problem)
            if problems:
                failed.append(name if required else f"{name} (advisory)")
            else:
                print(f"{len(examples)} examples as expected")
    if failed:
        print(f"doc examples: failures in {', '.join(failed)}")
    return 1 if any("(advisory)" not in name for name in failed) else 0


if __name__ == "__main__":
    sys.exit(main())
