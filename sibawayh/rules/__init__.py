"""The i'rab rule layer: structure and morphology in, named roles out.

A rule is a predicate over `(token, head, sentence)` returning
`(irab_role, rule_id, evidence)`. The registry orders them by priority and the
first match wins; no rule firing means abstention, never a guess.

`apply_rules` is the pipeline stage. It is the **only** place `irab_role` is
ever written — the parser supplies attachment and morphology supplies features,
and neither may name a role. That separation is why `Parse` holds integers and
why `parser_label` is documented as a token property rather than an edge label.

    tokens = apply_rules(tokens)

The skeleton ships with two rules, in `starter.py`. The real inventory follows.
"""

from __future__ import annotations

from collections.abc import Sequence

from sibawayh.rules.base import (
    Evidence,
    Finding,
    Predicate,
    Registry,
    Rule,
    RuleError,
)
from sibawayh.rules.starter import STARTER_RULES, starter_registry
from sibawayh.schema import ROOT_HEAD, Source, Token

__all__ = [
    "STARTER_RULES",
    "Evidence",
    "Finding",
    "Predicate",
    "Registry",
    "Rule",
    "RuleError",
    "apply_rules",
    "starter_registry",
]


def _head_of(token: Token, tokens: Sequence[Token]) -> Token | None:
    """The governing token, or `None` at the root or before parsing."""
    if token.head is None or token.head == ROOT_HEAD:
        return None
    for candidate in tokens:
        if candidate.id == token.head:
            return candidate
    return None


def apply_rules(tokens: Sequence[Token], registry: Registry | None = None) -> list[Token]:
    """Return copies of `tokens` carrying whatever roles the rules could derive.

    Pure: the tokens handed in are not touched. A token no rule matched comes
    back **unchanged** — `irab_role` stays `None`, and the layers above are
    expected to show morphology and say the syntax is uncertain rather than
    print a blank where a role should be.

    Evidence accumulates. A rule appends its reasons to whatever earlier stages
    recorded, so an inserted pronoun keeps the note explaining why it exists as
    well as the note explaining what it is.
    """
    registry = registry if registry is not None else starter_registry()

    applied: list[Token] = []
    for token in tokens:
        finding = registry.first_match(token, _head_of(token, tokens), tokens)
        if finding is None:
            applied.append(token)
            continue
        applied.append(
            token.model_copy(
                update={
                    "irab_role": finding.role,
                    "rule_id": finding.rule_id,
                    "evidence": [*token.evidence, *finding.evidence],
                    "provenance": {**token.provenance, "irab_role": Source.RULES},
                }
            )
        )
    return applied
