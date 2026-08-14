"""الجملة الاسمية: مبتدأ and the three kinds of خبر.

Under Sibawayh convention the المبتدأ is the root of the sentence — CLAUDE.md's
scheme table, first row, and what `arcs.py` re-roots the tree to achieve. So
"is this the مبتدأ?" reduces to "is this the root, and is it a nominative
nominal?", which is a far cheaper question than any other scheme would allow.

The خبر then hangs off it, and comes in three shapes, all of which tier 1 tests:

============================  =========================  ==========================
shape                         example                    what marks it
============================  =========================  ==========================
مفرد                          الشمس **مشرقة**            a nominal, definiteness disagreeing
جملة فعلية                    محمد **يقرأ** الكتاب       a verb under the مبتدأ
شبه جملة                      العصفور **في** القفص       a preposition or ظرف
============================  =========================  ==========================

The first of those is the one that can go wrong. A nominative adjective under a
nominative noun is a صفة when definiteness *agrees* and the خبر when it does
not — see `modifiers.py`, which owns the agreeing case and outranks this file.
Nothing structural separates them.

The شبه جملة rules live here rather than in `modifiers.py` because gold names
these tokens by the slot they fill, not by their part of speech:
`حرف جر — خبر شبه جملة`, `ظرف مكان — خبر شبه جملة`. The rule that knows the
token is the خبر is the one that can say so. Same reasoning puts `مبتدأ — مضاف`
here rather than in `idafa.py`.
"""

from __future__ import annotations

from collections.abc import Sequence

from sibawayh.rules.base import Evidence, Rule
from sibawayh.schema import ROOT_HEAD, Case, Pos, State, Token

NOMINAL = frozenset({Pos.NOUN, Pos.PROPN, Pos.PRON, Pos.ADJ})


def _is_topic(token: Token) -> bool:
    """A nominative nominal at the root — the المبتدأ, by our convention."""
    return (
        token.head == ROOT_HEAD
        and token.pos in NOMINAL
        and token.feats.case is Case.NOM
        and not token.inserted
    )


def _topic(*, construct: bool):
    """Build the predicate for the المبتدأ, with or without an إضافة under it."""

    def when(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
        if head is not None or not _is_topic(token):
            return None
        if (token.feats.state is State.CONSTRUCT) is not construct:
            return None
        evidence = ["sentence_initial", "is_root", f"pos={token.pos}", "case=nom"]
        if construct:
            evidence.append("state=construct")
        return evidence

    return when


def _predicate_of_topic(token: Token, head: Token | None) -> bool:
    """Whether `token` hangs off the المبتدأ."""
    return head is not None and _is_topic(head)


def _single_predicate(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
    """خبر مفرد: a nominal under the مبتدأ whose definiteness does *not* agree."""
    if token.pos not in NOMINAL or not _predicate_of_topic(token, head):
        return None
    assert head is not None
    if token.feats.case is not Case.NOM:
        return None
    if token.feats.state is None or head.feats.state is None:
        return None
    definite = token.feats.state in {State.DEF, State.CONSTRUCT}
    head_definite = head.feats.state in {State.DEF, State.CONSTRUCT}
    if definite is head_definite:
        return None  # agreement makes it a صفة — see modifiers.py
    return [
        f"head_form={head.form}",
        "head_is_topic",
        "case=nom",
        f"state={token.feats.state}",
        "definiteness_disagrees",
    ]


def _verbal_predicate(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
    """خبر جملة فعلية: a verb under the مبتدأ."""
    if token.pos is not Pos.VERB or not _predicate_of_topic(token, head):
        return None
    assert head is not None
    return [f"head_form={head.form}", "head_is_topic", "pos=verb"]


def _prepositional_predicate(
    token: Token, head: Token | None, tokens: Sequence[Token]
) -> Evidence | None:
    """خبر شبه جملة headed by a preposition."""
    if token.pos is not Pos.PREP or not _predicate_of_topic(token, head):
        return None
    assert head is not None
    return [f"head_form={head.form}", "head_is_topic", "pos=prep"]


def _adverbial_predicate(
    token: Token, head: Token | None, tokens: Sequence[Token]
) -> Evidence | None:
    """خبر شبه جملة headed by a ظرف — an accusative noun in construct state.

    CATiB has no adverb tag and CAMeL calls فوق a noun, so the ظرف is recognised
    by what it does: accusative on adverbiality, and governing a genitive as
    مضاف.
    """
    if token.pos is not Pos.NOUN or not _predicate_of_topic(token, head):
        return None
    assert head is not None
    if token.feats.case is not Case.ACC or token.feats.state is not State.CONSTRUCT:
        return None
    return [
        f"head_form={head.form}",
        "head_is_topic",
        "case=acc",
        "state=construct",
        "governs_a_genitive",
    ]


TOPIC = Rule(
    id="TOPIC",
    role="مبتدأ",
    priority=80,
    when=_topic(construct=False),
    description="The nominative nominal at the root of a nominal sentence.",
)

TOPIC_ANNEXING = Rule(
    id="TOPIC_ANNEXING",
    role="مبتدأ — مضاف",
    priority=75,
    when=_topic(construct=True),
    description="A مبتدأ that is itself the first term of an إضافة.",
)

PREDICATE_SINGLE = Rule(
    id="PREDICATE_SINGLE",
    role="خبر",
    priority=85,
    when=_single_predicate,
    description="خبر مفرد — a nominal whose definiteness disagrees with the مبتدأ.",
)

PREDICATE_VERBAL = Rule(
    id="PREDICATE_VERBAL",
    role="خبر — جملة فعلية",
    priority=85,
    when=_verbal_predicate,
    description="خبر جملة فعلية — a whole verbal sentence serving as the predicate.",
)

PREDICATE_PREPOSITIONAL = Rule(
    id="PREDICATE_PREPOSITIONAL",
    role="حرف جر — خبر شبه جملة",
    priority=85,
    when=_prepositional_predicate,
    description="خبر شبه جملة headed by a preposition.",
)

PREDICATE_ADVERBIAL = Rule(
    id="PREDICATE_ADVERBIAL",
    role="ظرف مكان — خبر شبه جملة",
    priority=85,
    when=_adverbial_predicate,
    description="خبر شبه جملة headed by an adverbial noun governing a genitive.",
)

NOMINAL_RULES = (
    TOPIC_ANNEXING,
    TOPIC,
    PREDICATE_SINGLE,
    PREDICATE_VERBAL,
    PREDICATE_PREPOSITIONAL,
    PREDICATE_ADVERBIAL,
)
