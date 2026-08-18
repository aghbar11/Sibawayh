"""The renderer contract: an analysis in, Arabic prose out, nothing else.

A renderer answers one question — how do we say this to the student — and
answers it with strings. It never sees a rule, never sets a role, and cannot
change a token. That is the same firewall `parsers/base.py` builds around
attachment, for the same reason: CLAUDE.md's position is that the LLM renders
and does not decide, and a return type that carries only text makes ignoring
that impossible rather than merely discouraged.

Two backends will implement this. One is deterministic tables and runs offline;
one calls a model and can fail, cost money, or hallucinate. The interface is
written before either so that it fits both, and so the second can be swapped out
at a demo without touching anything upstream.

A renderer is a **component**, not a pipeline stage. Stages are pure functions
over tokens, and prose is not a token field — `Token` forbids extra keys, and
widening the schema to carry display text would let a renderer write onto the
analysis it is supposed to only describe. So `Renderer.render` returns a
`Rendering`, and `describe` is the thin function that runs it and checks the
result lines up with the tokens it was asked about.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from sibawayh.schema import Token


class RenderError(RuntimeError):
    """A renderer could not produce usable prose."""


@dataclass(frozen=True)
class Rendering:
    """One renderer's answer for one sentence.

    `lines[i]` is the إعراب of token `i + 1`, positionally matching `Token.id`
    the way `Parse.heads` does, or `None` where the renderer declined to say
    anything about that token.

    `None` is not a failure. A token the rules abstained on has no role to state,
    and a renderer that invented prose for it would be doing exactly what
    abstention exists to prevent. The caller shows morphology there instead.
    """

    lines: tuple[str | None, ...]

    def __post_init__(self) -> None:
        blank = [
            position
            for position, line in enumerate(self.lines, start=1)
            if line is not None and not line.strip()
        ]
        if blank:
            raise RenderError(
                f"tokens {blank} got an empty line; use None to decline, not whitespace"
            )

    @classmethod
    def of(cls, lines: Sequence[str | None]) -> Rendering:
        """Build from any sequence, so backends need not care about tuples."""
        return cls(tuple(lines))

    def line_for(self, position: int) -> str | None:
        """The line for the 1-based token `position`, or `None` if declined."""
        return self.lines[position - 1]

    @property
    def described(self) -> int:
        """How many tokens the renderer was willing to describe."""
        return sum(1 for line in self.lines if line is not None)


class Renderer(ABC):
    """A backend that turns an analyzed sentence into Arabic إعراب prose.

    Implementations receive the whole sentence, not one token at a time, because
    a token's line can depend on its neighbours — a جار ومجرور is described as a
    pair, and a clause is described by the role of the clause. They must not
    mutate what they are given.

    `deterministic` says whether the same sentence always produces the same
    prose. The template backend is; a model is not. Tests compare against fixed
    strings only where this holds, and a caller may cache only where it holds.
    """

    name: str = "renderer"

    deterministic: bool = False
    """True when output depends on nothing but the tokens handed in — no
    network, no sampling, no clock."""

    @abstractmethod
    def render(self, tokens: Sequence[Token]) -> Rendering:
        """One line per token, in order."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        kind = "deterministic" if self.deterministic else "generative"
        return f"<{type(self).__name__} {self.name} {kind}>"


def describe(tokens: Sequence[Token], renderer: Renderer) -> Rendering:
    """Run `renderer` over `tokens` and check the answer lines up.

    Takes tokens and not a `Sentence`, matching `attach`, so the two components
    are called the same way.

    Pure, and the only place a renderer's output is length-checked, so a backend
    that returns the wrong number of lines fails here rather than silently
    pairing one token's prose with another's word.
    """
    rendering = renderer.render(tokens)
    if len(rendering.lines) != len(tokens):
        raise RenderError(
            f"{renderer.name} returned {len(rendering.lines)} lines for {len(tokens)} tokens"
        )
    return rendering
