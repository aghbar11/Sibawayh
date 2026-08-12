"""Scaffold smoke test: the package imports and the layout is where we expect it."""

import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

MODULES = [
    "sibawayh",
    "sibawayh.arcs",
    "sibawayh.covert",
    "sibawayh.morphology",
    "sibawayh.normalize",
    "sibawayh.parsers",
    "sibawayh.render",
    "sibawayh.rules",
    "sibawayh.schema",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name: str) -> None:
    importlib.import_module(name)


def test_version_exposed() -> None:
    import sibawayh

    assert sibawayh.__version__


@pytest.mark.parametrize("relpath", ["data/eval", "data/ldc", "tests"])
def test_directory_exists(relpath: str) -> None:
    assert (REPO_ROOT / relpath).is_dir()


def test_licensed_data_is_gitignored() -> None:
    """data/ldc/ must never enter version control."""
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/ldc/" in gitignore
