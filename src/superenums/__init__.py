"""Rust-style enums for Python."""

from importlib.metadata import version

from superenums._core import (
    SuperEnumError,
    Variant,
    Variants,
    alias,
    namespace_of,
    variant_name,
    variants,
)

__version__ = version("superenums")

__all__ = [
    "SuperEnumError",
    "Variant",
    "Variants",
    "__version__",
    "alias",
    "namespace_of",
    "variant_name",
    "variants",
]
