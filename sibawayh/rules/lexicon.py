"""Closed-class word lists the rules key on, and how to match them.

Arabic syntax turns on a handful of small, fixed sets — كان وأخواتها,
إنّ وأخواتها, the jussive and subjunctive particles. Membership is a *lexical*
fact, not a morphological feature, so no analyser hands it to us and it has to
be written down.

Matching is diacritic-insensitive. CAMeL returns a vowelled lemma (`كانَ`,
`إِنَّ`) while a hand-written list is comfortable to read undiacritized, and the
eval set's gold lemmas are bare. Comparing the stripped forms lets both work
without either having to be wrong.
"""

from __future__ import annotations

from sibawayh.normalize import strip_diacritics, strip_tatweel
from sibawayh.schema import Token


def bare(text: str | None) -> str:
    """A lemma reduced to the form a word list can be written in."""
    if not text:
        return ""
    return strip_tatweel(strip_diacritics(text)).strip()


KANA_AND_SISTERS = frozenset(
    bare(lemma)
    for lemma in (
        "كان",  # be
        "صار",  # become
        "أصبح",  # become / be in the morning
        "أضحى",  # become / be at forenoon
        "أمسى",  # become / be in the evening
        "بات",  # become / be at night
        "ظل",  # remain
        "ليس",  # be not
        "زال",  # cease — ما زال
        "برح",  # cease — ما برح
        "فتئ",  # cease — ما فتئ
        "انفك",  # cease — ما انفك
        "دام",  # last — ما دام
    )
)
"""الأفعال الناقصة. They raise their اسم and put their خبر in the accusative,
which is the opposite of what a complete verb does to its arguments — so every
rule about فاعل and مفعول به has to exclude them."""

INNA_AND_SISTERS = frozenset(
    bare(lemma)
    for lemma in (
        "إن",  # indeed
        "أن",  # that
        "كأن",  # as though
        "لكن",  # but
        "ليت",  # would that
        "لعل",  # perhaps
    )
)
"""الحروف المشبهة بالفعل. Inverse case pattern to كان: the اسم is accusative and
the خبر nominative. `nasikh_inna_01` is the test."""

JUSSIVE_PARTICLES = frozenset(bare(lemma) for lemma in ("لم", "لما", "لا", "ل"))
"""أدوات الجزم that govern a following imperfect verb."""

SUBJUNCTIVE_PARTICLES = frozenset(bare(lemma) for lemma in ("لن", "أن", "كي", "لكي", "حتى", "إذن"))
"""أدوات النصب that govern a following imperfect verb."""


def lemma_in(token: Token, vocabulary: frozenset[str]) -> bool:
    """Whether `token`'s lemma — or its surface form — is in `vocabulary`.

    The surface form is a fallback for tokens that never went through morphology,
    which is how the eval set's inserted tokens and most hand-written test cases
    arrive.
    """
    return bare(token.lemma) in vocabulary or bare(token.form) in vocabulary


def is_defective_verb(token: Token) -> bool:
    """كان or one of its sisters — a فعل ناقص."""
    return lemma_in(token, KANA_AND_SISTERS)
