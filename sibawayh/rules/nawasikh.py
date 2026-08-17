"""النواسخ: كان وأخواتها and إنّ وأخواتها.

Both take an اسم and a خبر, and they assign **opposite** cases:

===============  ==============  ==============
عامل             اسم             خبر
===============  ==============  ==============
كان وأخواتها     nominative      accusative
إنّ وأخواتها     accusative      nominative
===============  ==============  ==============

So case alone cannot name either role — a nominative under a ناسخ is اسم كان or
خبر إنّ depending entirely on *which* ناسخ governs it. The head's lemma is the
discriminator, which is exactly what `nasikh_kana_01` and `nasikh_inna_01` are in
the eval set to prove. This is also the pattern the I3rab paper's Figure 11
records PADT getting structurally different from i'rab, and the reason both
arguments hang off the ناسخ rather than off each other.

`verbal.py` excludes these heads; this file claims them. Nothing here fires
unless the head is in one of the two closed lists in `lexicon.py`.
"""

from __future__ import annotations

from collections.abc import Sequence

from sibawayh.rules.base import Evidence, Rule
from sibawayh.rules.lexicon import INNA_AND_SISTERS, KANA_AND_SISTERS, lemma_in
from sibawayh.schema import Aspect, Case, Pos, Token

NOMINAL = frozenset({Pos.NOUN, Pos.PROPN, Pos.PRON, Pos.ADJ})


PARTICLE_POS = frozenset({Pos.PART, Pos.CONJ})
"""What إنّ can come back tagged as.

It is a حرف مشبه بالفعل, so `part` is the expected tag — but the BERT
disambiguator reads إنّ as `conj_sub`, which our collapse table maps to `conj`,
however, أنّ really does subordinate. Accepting either
keeps the rule working whichever analyser is in use, and the lemma check is what
actually identifies the family.
"""


def _argument_of(vocabulary: frozenset[str], case: Case, head_pos: frozenset[Pos], family: str):
    """Build the predicate for one argument of one ناسخ family."""

    def when(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
        if token.pos not in NOMINAL:
            return None
        if head is None or head.pos not in head_pos or not lemma_in(head, vocabulary):
            return None
        if token.feats.case is not case:
            return None
        return [
            f"head_form={head.form}",
            f"head_lemma_in_{family}",
            f"case={case}",
        ]

    return when


def _defective_verb(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
    """كان itself — a فعل ماضٍ ناقص."""
    if token.pos is not Pos.VERB or not lemma_in(token, KANA_AND_SISTERS):
        return None
    if head is not None and head.pos is not Pos.PART:
        return None
    if token.feats.aspect is not Aspect.PERFECT:
        return None
    return ["pos=verb", "lemma_in_kana_sisters", "aspect=perfect"]


KANA_VERB = Rule(
    id="KANA_VERB",
    role="فعل ماضٍ ناقص",
    priority=50,
    when=_defective_verb,
    description="كان or a sister: a verb that takes an اسم and a خبر rather than a فاعل.",
)

KANA_SUBJECT = Rule(
    id="KANA_SUBJECT",
    role="اسم كان",
    priority=55,
    when=_argument_of(KANA_AND_SISTERS, Case.NOM, frozenset({Pos.VERB}), "kana_sisters"),
    description="The nominative argument of كان — raised, where a complete verb's would be فاعل.",
)

KANA_PREDICATE = Rule(
    id="KANA_PREDICATE",
    role="خبر كان",
    priority=55,
    when=_argument_of(KANA_AND_SISTERS, Case.ACC, frozenset({Pos.VERB}), "kana_sisters"),
    description="The accusative argument of كان — its خبر, not a مفعول به.",
)

INNA_SUBJECT = Rule(
    id="INNA_SUBJECT",
    role="اسم إنّ",
    priority=55,
    when=_argument_of(INNA_AND_SISTERS, Case.ACC, PARTICLE_POS, "inna_sisters"),
    description="The accusative argument of إنّ — the inverse of كان's pattern.",
)

INNA_PREDICATE = Rule(
    id="INNA_PREDICATE",
    role="خبر إنّ",
    priority=55,
    when=_argument_of(INNA_AND_SISTERS, Case.NOM, PARTICLE_POS, "inna_sisters"),
    description="The nominative argument of إنّ — its خبر, not its اسم.",
)

NAWASIKH_RULES = (
    KANA_VERB,
    KANA_SUBJECT,
    KANA_PREDICATE,
    INNA_SUBJECT,
    INNA_PREDICATE,
)
