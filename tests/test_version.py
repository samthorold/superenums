import tomllib
from pathlib import Path

import superenums

PYPROJECT = Path(__file__).parents[1] / "pyproject.toml"


def test_version_matches_pyproject() -> None:
    with PYPROJECT.open("rb") as f:
        expected = tomllib.load(f)["project"]["version"]

    assert superenums.__version__ == expected
