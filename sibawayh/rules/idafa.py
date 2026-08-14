"""الإضافة: مضاف and مضاف إليه.

The construct state is the whole signal, and it comes from morphology rather
than from the tree: CAMeL's `stt=c` becomes `state=construct`, and CLAUDE.md
calls `idafa_01` the test that this is wired through. Without it, كتاب الطالب
and الكتاب الجديد are the same shape — a nominal with a nominal hanging off it —
and only the state and the case tell them apart.

Two conditions, both required: the **head** is in the construct state, and the
**dependent** is genitive. Either alone is not enough. A construct noun with a
non-genitive dependent is not an إضافة, and a genitive under a non-construct
head wants a preposition, which is `modifiers.py`'s.

The مضاف itself gets no rule here. Gold names it by its *syntactic* role with
the إضافة appended — `مبتدأ — مضاف` — so the rule that knows it is the مبتدأ is
the one that can say so, and it lives in `nominal.py`. Recording it twice would
mean two rules competing to name one token.
"""

from __future__ import annotations

from collections.abc import Sequence

from sibawayh.rules.base import Evidence, Rule
from sibawayh.schema import Case, Pos, State, Token

NOMINAL = frozenset({Pos.NOUN, Pos.PROPN, Pos.PRON, Pos.ADJ})


def _annexed(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
    """A genitive nominal under a noun in the construct state."""
    if token.pos not in NOMINAL or token.feats.case is not Case.GEN:
        return None
    if head is None or head.pos not in NOMINAL:
        return None
    if head.feats.state is not State.CONSTRUCT:
        return None
    return [
        "case=gen",
        f"head_form={head.form}",
        "head_state=construct",
    ]


IDAFA_ANNEXED = Rule(
    id="IDAFA_ANNEXED",
    role="مضاف إليه",
    priority=60,
    when=_annexed,
    description="The genitive possessor under a noun in construct state.",
)

IDAFA_RULES = (IDAFA_ANNEXED,)
