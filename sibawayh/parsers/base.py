"""The parser contract: attachment in, attachment out, nothing else.

A parser answers one question — which token governs which — and answers it with
integers. It never sees a role, never sets one, and cannot invent or drop a
token. That is deliberate: `parser_label` and `irab_role` are separate fields
throughout, and a return type that carries only head indices makes conflating
them impossible rather than merely discouraged.

The interface is written before any backend exists, on purpose. Two will
implement it — one free and shippable, one trained on licensed data and
evaluation-only — and an interface shaped around whichever came first would not
fit the second.

A parser is a **component**, not a pipeline stage. Stages are pure functions over
tokens; `Parser.parse` returns a `Parse`, and `attach` is the stage that applies
it. Keeping them apart means evaluation compares two lists of integers, and the
bookkeeping of writing heads onto tokens lives in one place instead of once per
backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from sibawayh.schema import ROOT_HEAD, Token


class ParserError(RuntimeError):
    """A parser could not produce a usable attachment."""


class Formalism(StrEnum):
    """The annotation convention a set of arcs follows.

    Heads are integers, so a `Parse` alone does not say what convention produced
    them — and the conventions disagree structurally, not just in vocabulary. UD
    makes a preposition a dependent of its object; CATiB and PADT make it the
    head; i'rab roots a nominal sentence at the مبتدأ where the others root it at
    the predicate.

    A backend declares which one it speaks so arc normalization can dispatch
    instead of assuming. That is what keeps a second backend costing one
    normalizer rather than a rewrite.
    """

    CATIB = "catib"
    UD = "ud"
    PADT = "padt"
    """Prague analytical functions — step 22's evaluation-only backend."""

    IRAB = "irab"
    """Not a backend's answer but the target: what arc normalization produces."""


@dataclass(frozen=True)
class Parse:
    """One parser's answer for one sentence.

    `heads[i]` is the id of the token governing token `i + 1`, or `ROOT_HEAD` for
    the token that heads the sentence. Ids are 1-based, matching `Token.id`.

    `confidence[i]` is how sure the parser is of *that arc*, in 0..1, or `None`
    where the backend cannot say. It is an input to the per-token confidence that
    the abstention layer computes later, not that number itself.

    Structural checks here are about the return value being usable at all —
    right length, ids in range. Whether the result is a well-formed single-rooted
    tree is a separate question, and a later one.
    """

    heads: tuple[int, ...]
    confidence: tuple[float | None, ...] = field(default=())

    def __post_init__(self) -> None:
        count = len(self.heads)
        if self.confidence and len(self.confidence) != count:
            raise ParserError(f"got {len(self.confidence)} confidences for {count} heads")
        out_of_range = [head for head in self.heads if not ROOT_HEAD <= head <= count]
        if out_of_range:
            raise ParserError(f"heads {out_of_range} fall outside 0..{count}")
        for position, head in enumerate(self.heads, start=1):
            if head == position:
                raise ParserError(f"token {position} is its own head")

    @classmethod
    def of(
        cls,
        heads: Sequence[int],
        confidence: Sequence[float | None] | None = None,
    ) -> Parse:
        """Build from any sequences, so backends need not care about tuples."""
        return cls(tuple(heads), tuple(confidence) if confidence is not None else ())

    def confidence_for(self, position: int) -> float | None:
        """Arc confidence for the 1-based token `position`, or `None`."""
        if not self.confidence:
            return None
        return self.confidence[position - 1]


class Parser(ABC):
    """A backend that assigns head indices to already-analyzed tokens.

    Implementations receive tokens carrying morphology and return a `Parse`. They
    must not mutate the tokens they are given.

    `eval_only` marks a backend whose training data forbids shipping. It is a
    declaration, not yet an enforcement — the gate that reads it arrives with the
    backend that needs it.

    `formalism` says which annotation convention the returned heads follow. Two
    declarations, two different consumers: the licence gate reads one, arc
    normalization reads the other. Neither tells a caller *which backend* is
    running, which stays private to this package.
    """

    name: str = "parser"

    eval_only: bool = False
    """True when this backend may never reach production. See `docs/PLAN.md`
    under data assets: a model trained on PADT inherits PADT's licence."""

    formalism: Formalism
    """The convention the heads follow. Deliberately has no default: a wrong
    guess here silently mis-normalizes every arc, and there is no honest default
    to guess. Subclasses must say, and `__init_subclass__` enforces it."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject a backend that does not declare its formalism.

        Failing at class-definition time rather than at first attribute access
        matters here: the symptom of a missing declaration would otherwise be
        wrongly normalized arcs somewhere downstream, which looks like a parsing
        bug rather than a missing line.
        """
        super().__init_subclass__(**kwargs)
        if getattr(cls, "formalism", None) is None:
            raise TypeError(f"{cls.__name__} must declare `formalism`")

    @abstractmethod
    def parse(self, tokens: Sequence[Token]) -> Parse:
        """Head indices for `tokens`, one per token, in order."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        gate = ", eval_only" if self.eval_only else ""
        return f"<{type(self).__name__} {self.name} {self.formalism}{gate}>"
