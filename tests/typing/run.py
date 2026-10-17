"""Run the type-level test suite: every case file under each type checker.

The case files in ``cases/`` are typeshed-style: code that must type-check
cleanly, ``assert_type(...)`` for expected narrowing, and ignore comments on
the lines that must produce an error.

Ignore-comment scheme
---------------------
Each checker is configured to honour only its own ignore comment, with
unused-ignore detection on, so a line that must error carries one comment per
checker and each one asserts that checker's error (one line in a case file):

    assert_never(s)  # type: ignore[arg-type]
                     # pyright: ignore[reportArgumentType]
                     # ty: ignore[type-assertion-failure]

- mypy reads ``# type: ignore[code]`` (``warn_unused_ignores``, ``mypy.ini``).
- pyright reads ``# pyright: ignore[rule]`` only (``enableTypeIgnoreComments``
  off, ``reportUnnecessaryTypeIgnoreComment`` on, ``pyrightconfig.json``).
- ty reads ``# ty: ignore[rule]`` only (``respect-type-ignore-comments`` off,
  ``unused-ignore-comment`` an error, ``ty.toml``).

If an expected error disappears, its comment becomes unused and that checker
fails. A comment for only some checkers records where checkers disagree.

Pyright skips unreachable code entirely, including unused-ignore detection, so
it would silently accept a "missing variant" case that became exhaustive. The
suite therefore turns on ``reportUnreachable``: a complete match's
``case _: assert_never(s)`` arm carries ``# pyright: ignore[reportUnreachable]``,
which is pyright's positive proof that the match is exhaustive.

pyright and mypy failures fail the run. ty is pre-1.0, so its result is
reported but never fails the run.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE / "cases"

# (name, command, working directory, fails the build)
CHECKERS: list[tuple[str, list[str], Path, bool]] = [
    ("pyright", ["pyright", "-p", str(HERE)], HERE, True),
    ("mypy", ["mypy", "--config-file", str(HERE / "mypy.ini"), "."], CASES, True),
    ("ty", ["ty", "check", "--config-file", str(HERE / "ty.toml"), "."], CASES, False),
]


def main() -> int:
    failed: list[str] = []
    for name, command, cwd, required in CHECKERS:
        print(f"--- {name} ---", flush=True)
        returncode = subprocess.run(command, cwd=cwd, check=False).returncode
        if returncode != 0:
            failed.append(name if required else f"{name} (advisory)")
    if failed:
        print(f"type-level suite: failures in {', '.join(failed)}")
    else:
        print("type-level suite: all checkers passed")
    return 1 if any("(advisory)" not in name for name in failed) else 0


if __name__ == "__main__":
    sys.exit(main())
