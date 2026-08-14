"""Two rules, chosen to prove the shape rather than to cover the language.

The real inventory — roughly forty rules across verbal, nominal, nawasikh,
idafa, modifiers and particles — is the next step. These two are here because
the engine is not worth reviewing empty, and they were picked for being the
least likely to need revising when the rest arrive:

* an inserted pronoun is a فاعل **by construction** — `covert.py` inserts it
  precisely when a verb has no overt agent, so the conclusion is already earned
* a token governed by a preposition is مجرور **by definition** — under Sibawayh
  convention the preposition is the عامل and heads its object, which is exactly
  what arc normalization guarantees

Both carry their evidence in hint order: locate the token, identify the عامل,
then name the role.
"""

from __future__ import annotations

from collections.abc import Sequence

from sibawayh.rules.base import Evidence, Registry, Rule
from sibawayh.schema import Pos, Token


def _covert_agent(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
    """An inserted pronoun hanging off a verb."""
    if not token.inserted or token.pos is not Pos.PRON:
        return None
    if head is None or head.pos is not Pos.VERB:
        return None
    return ["inserted_by_us", "head_pos=verb", "verb_has_no_overt_agent"]


def _preposition_object(
    token: Token, head: Token | None, tokens: Sequence[Token]
) -> Evidence | None:
    """Anything governed by a حرف جر."""
    if head is None or head.pos is not Pos.PREP:
        return None
    evidence = ["head_pos=prep", f"head_form={head.form}"]
    if token.feats.case is not None:
        evidence.append(f"case={token.feats.case}")
    return evidence


COVERT_AGENT = Rule(
    id="COVERT_AGENT",
    role="فاعل — ضمير مستتر",
    priority=10,
    when=_covert_agent,
    description="An inserted pronoun under a verb is its agent; that is why it was inserted.",
)

PREP_OBJECT = Rule(
    id="PREP_OBJECT",
    role="مجرور",
    priority=20,
    when=_preposition_object,
    description="A preposition governs its object in the genitive.",
)

STARTER_RULES = (COVERT_AGENT, PREP_OBJECT)


def starter_registry() -> Registry:
    """A fresh registry holding the starter rules, in priority order."""
    return Registry(STARTER_RULES)
