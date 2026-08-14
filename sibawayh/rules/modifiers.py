"""المتعلقات: صفة and what a preposition governs.

**صفة is separated from خبر by definiteness, not by anything structural.** In
الكتاب الجديد مفيد both adjectives hang off الكتاب in the nominative — same POS,
same case, same arc. الجديد is definite like its noun and is therefore a صفة;
مفيد is indefinite and is therefore the خبر. CLAUDE.md flags this as the
confusion the rule engine will make, and `sifa_01` is the test.

Agreement is checked on the **functional** `gen`/`num`, never `form_gen`/
`form_num` — the distinction CLAUDE.md insists on and the reason `morphology.py`
keeps them apart.

حال and تمييز have no rules. Neither appears in tier 1, so there is no gold to
verify against, and a rule written blind would be a guess wearing a role name.
They arrive with the tier-2 sentences.
"""

from __future__ import annotations

from collections.abc import Sequence

from sibawayh.rules.base import Evidence, Rule
from sibawayh.schema import Pos, State, Token

DEFINITE = frozenset({State.DEF, State.CONSTRUCT})
"""Both count as definite for agreement. A construct noun takes its definiteness
from what follows it, and صفة agreement follows suit."""


def _is_definite(token: Token) -> bool | None:
    """True, False, or `None` when the state was never determined."""
    if token.feats.state is None or token.feats.state is State.UNKNOWN:
        return None
    return token.feats.state in DEFINITE


def _adjectival_modifier(
    token: Token, head: Token | None, tokens: Sequence[Token]
) -> Evidence | None:
    """An adjective agreeing with its noun in definiteness and case."""
    if token.pos is not Pos.ADJ or head is None:
        return None
    if head.pos not in {Pos.NOUN, Pos.PROPN, Pos.PRON}:
        return None
    if token.feats.case is None or token.feats.case is not head.feats.case:
        return None

    definite, head_definite = _is_definite(token), _is_definite(head)
    if definite is None or head_definite is None or definite is not head_definite:
        return None

    evidence = [
        f"head_form={head.form}",
        f"case={token.feats.case}=head_case",
        "definiteness_agrees",
        f"state={token.feats.state}",
    ]
    if token.feats.gen is not None and token.feats.gen is head.feats.gen:
        evidence.append(f"gen={token.feats.gen}=head_gen")
    if token.feats.num is not None and token.feats.num is head.feats.num:
        evidence.append(f"num={token.feats.num}=head_num")
    return evidence


def _preposition_object(
    token: Token, head: Token | None, tokens: Sequence[Token]
) -> Evidence | None:
    """Anything governed by a حرف جر.

    True by definition rather than by inference: under Sibawayh convention the
    preposition is the عامل and heads its object, which is what `arcs.py`
    guarantees.
    """
    if head is None or head.pos is not Pos.PREP:
        return None
    evidence = ["head_pos=prep", f"head_form={head.form}"]
    if token.feats.case is not None:
        evidence.append(f"case={token.feats.case}")
    return evidence


ADJECTIVE = Rule(
    id="ADJECTIVE",
    role="صفة",
    priority=70,
    when=_adjectival_modifier,
    description="An adjective agreeing with its noun in definiteness — not a خبر.",
)

PREP_OBJECT = Rule(
    id="PREP_OBJECT",
    role="مجرور",
    priority=20,
    when=_preposition_object,
    description="A preposition governs its object in the genitive.",
)

MODIFIER_RULES = (PREP_OBJECT, ADJECTIVE)
