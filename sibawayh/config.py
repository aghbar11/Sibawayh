"""Reading settings, and keys, from the environment or from a `.env` file.

A key typed into a shell lands in shell history and in the process list. A key in
a file that `.gitignore` already covers does not, and `.gitignore` has covered
`.env` since the repository was set up. So both are read, and the real
environment wins where they disagree — that is the usual precedence, and it is
what lets CI or a container override a file left over on a developer's machine.

**Nothing is mutated.** `os.environ` is read, never written to. A library that
edits the environment of the program that imported it is a library that surprises
someone eventually, and there is no need: the lookup can simply consult both.

The file is searched for from the working directory upwards, so a command run
from inside `tests/` or `scripts/` finds the same file as one run from the root.
Parsing is deliberately small — `KEY=value`, one per line, `#` starts a comment,
and quotes around the value are stripped. Anything more is a configuration format
this project has not needed.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

ENV_FILE = ".env"
ENV_FILE_VAR = "SIBAWAYH_ENV_FILE"
"""Points at a file somewhere else. Useful for a second key, or for a test."""


def _parse(text: str) -> dict[str, str]:
    values = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if name:
            values[name] = value
    return values


def find_env_file(start: Path | None = None) -> Path | None:
    """The nearest `.env` at or above `start`, or `None`.

    `$SIBAWAYH_ENV_FILE` overrides the search entirely, and is not required to
    exist — a path that was set and is wrong should read as empty rather than as
    "no file was configured".
    """
    named = os.environ.get(ENV_FILE_VAR)
    if named:
        return Path(named)
    here = (start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        candidate = directory / ENV_FILE
        if candidate.is_file():
            return candidate
    return None


@lru_cache(maxsize=8)
def _file_values(path: Path) -> dict[str, str]:
    try:
        return _parse(path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def env_file_values(start: Path | None = None) -> dict[str, str]:
    """Everything the nearest `.env` sets. Empty if there is none."""
    path = find_env_file(start)
    return dict(_file_values(path)) if path else {}


def setting(name: str, default: str = "") -> str:
    """The value of `name`, from the real environment or else from `.env`.

    The environment wins, so a key exported for one command overrides the file
    for that command without anyone having to edit it.
    """
    from_environment = os.environ.get(name)
    if from_environment:
        return from_environment
    return env_file_values().get(name, default)


def forget_env_files() -> None:
    """Drop the parsed-file cache. For tests, and for a key changed mid-session."""
    _file_values.cache_clear()
