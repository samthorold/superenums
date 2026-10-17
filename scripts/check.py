"""Run every check: runtime tests, the type-level suite, strict checks, lint, format.

Usage: uv run scripts/check.py
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STEPS: list[tuple[str, list[str]]] = [
    ("pytest", ["pytest", "-q"]),
    ("type-level suite", [sys.executable, "tests/typing/run.py"]),
    ("pyright (strict, src)", ["pyright"]),
    ("mypy (strict, src)", ["mypy"]),
    ("ruff lint", ["ruff", "check", "."]),
    ("ruff format", ["ruff", "format", "--check", "."]),
]


def main() -> int:
    start = time.monotonic()
    failed: list[str] = []
    for name, command in STEPS:
        print(f"=== {name} ===", flush=True)
        if subprocess.run(command, cwd=ROOT, check=False).returncode != 0:
            failed.append(name)
    elapsed = time.monotonic() - start
    if failed:
        print(f"FAILED ({elapsed:.1f}s): {', '.join(failed)}")
        return 1
    print(f"All checks passed ({elapsed:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
