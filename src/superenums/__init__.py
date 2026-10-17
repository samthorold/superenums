"""Rust-style enums for Python."""

from importlib.metadata import version

from superenums._core import (
    SuperEnumError,
    Variant,
    variant_name,
    variants,
)

__version__ = version("superenums")

__all__ = [
    "SuperEnumError",
    "Variant",
    "__version__",
    "variant_name",
    "variants",
]
