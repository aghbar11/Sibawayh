"""Tests for reading settings from the environment or a `.env` file."""

from __future__ import annotations

from pathlib import Path

import pytest
from sibawayh.config import (
    ENV_FILE_VAR,
    env_file_values,
    find_env_file,
    forget_env_files,
    setting,
)


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither a stray `.env` above the repository nor a cached read of one may
    decide the outcome of a test."""
    monkeypatch.delenv(ENV_FILE_VAR, raising=False)
    forget_env_files()


def write_env(directory: Path, text: str) -> Path:
    path = directory / ".env"
    path.write_text(text, encoding="utf-8")
    return path


# --- parsing ------------------------------------------------------------------------


def test_a_key_is_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_FILE_VAR, str(write_env(tmp_path, "GEMINI_API_KEY=abc123\n")))
    assert setting("GEMINI_API_KEY") == "abc123"


def test_quotes_around_a_value_are_stripped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_FILE_VAR, str(write_env(tmp_path, "K=\"quoted\"\nJ='single'\n")))
    assert env_file_values() == {"K": "quoted", "J": "single"}


def test_comments_and_blank_lines_are_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_FILE_VAR, str(write_env(tmp_path, "# a note\n\nK=v\n")))
    assert env_file_values() == {"K": "v"}


def test_an_export_prefix_is_tolerated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """People paste the line they used in a shell."""
    monkeypatch.setenv(ENV_FILE_VAR, str(write_env(tmp_path, "export K=v\n")))
    assert env_file_values() == {"K": "v"}


def test_a_value_containing_an_equals_sign_survives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keys are base64-ish and do contain them."""
    monkeypatch.setenv(ENV_FILE_VAR, str(write_env(tmp_path, "K=a=b=c\n")))
    assert env_file_values() == {"K": "a=b=c"}


# --- precedence ---------------------------------------------------------------------


def test_the_real_environment_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """So a key exported for one command overrides the file without anyone
    editing it."""
    monkeypatch.setenv(ENV_FILE_VAR, str(write_env(tmp_path, "K=from-file\n")))
    monkeypatch.setenv("K", "from-environment")
    assert setting("K") == "from-environment"


def test_a_missing_setting_gives_the_default() -> None:
    assert setting("SIBAWAYH_NOTHING_IS_SET_HERE", "fallback") == "fallback"


def test_nothing_is_written_to_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A library that edits the environment of the program that imported it
    surprises someone eventually."""
    import os

    monkeypatch.setenv(ENV_FILE_VAR, str(write_env(tmp_path, "SIBAWAYH_ONLY_IN_FILE=x\n")))
    assert setting("SIBAWAYH_ONLY_IN_FILE") == "x"
    assert "SIBAWAYH_ONLY_IN_FILE" not in os.environ


# --- finding the file ---------------------------------------------------------------


def test_the_file_is_found_from_a_subdirectory(tmp_path: Path) -> None:
    """A command run from inside tests/ finds the same file as one run from the
    repository root."""
    write_env(tmp_path, "K=v\n")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert find_env_file(deep) == tmp_path / ".env"


def test_no_file_is_not_an_error(tmp_path: Path) -> None:
    assert find_env_file(tmp_path) is None
    assert env_file_values(tmp_path) == {}


def test_a_configured_path_that_does_not_exist_reads_as_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path that was set and is wrong should not silently fall back to a search
    that finds some other file."""
    monkeypatch.setenv(ENV_FILE_VAR, str(tmp_path / "absent.env"))
    assert env_file_values() == {}


def test_the_repository_ignores_dot_env() -> None:
    """The key must not be committable. This is the line that stops it."""
    ignored = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in ignored.splitlines()
