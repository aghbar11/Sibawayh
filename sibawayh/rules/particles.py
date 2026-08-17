"""الحروف: the particles that govern, named for what they do.

A particle's own i'rab entry says which case or mood it imposes, not what it
means. لم is حرف جزم because it puts the following imperfect in the jussive;
لن is حرف نصب because it puts it in the subjunctive. Under Sibawayh convention
the particle **heads** the verb it governs — the I3rab paper's Figure 16 — so
`arcs.py` has already put the verb underneath it by the time these rules run.

إنّ is also حرف نصب, by a different route: it makes its اسم accusative. Same
role string, separate rule, because the evidence differs and the hint text will
too — one explains mood, the other case.

جر is not here. A preposition's own entry in the eval set comes bundled with the
role it fills (`حرف جر — خبر شبه جملة`), so it lives with the خبر rules in
`nominal.py`; what hangs *underneath* it is `modifiers.py`'s.
"""

from __future__ import annotations

from collections.abc import Sequence

from sibawayh.rules.base import Evidence, Rule
from sibawayh.rules.lexicon import (
    INNA_AND_SISTERS,
    JUSSIVE_PARTICLES,
    SUBJUNCTIVE_PARTICLES,
    lemma_in,
)
from sibawayh.schema import Aspect, Mood, Pos, Token


def _governing_particle(vocabulary: frozenset[str], mood: Mood, family: str):
    """Build the predicate for a particle that governs a verb's mood.

    The verb's *reported* mood is not required to match. Undiacritized يقرأ
    carries no mood — every analysis comes back `mod:u` — so demanding
    `mood is JUSSIVE` would mean لم is never recognised on exactly the input
    students type. What identifies the particle is its lemma and the fact that
    it governs an imperfect verb; the mood is what it *imposes*, not evidence
    for what it is.
    """

    def when(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
        if token.pos is not Pos.PART or not lemma_in(token, vocabulary):
            return None
        governed = [
            other
            for other in tokens
            if other.head == token.id
            and other.pos is Pos.VERB
            # Not `is IMPERFECT`: gold sets aspect *or* mood on a verb, never
            # both, so an unset aspect has to be acceptable. Only an explicitly
            # perfect verb is disqualified — a جازم never governs one.
            and other.feats.aspect is not Aspect.PERFECT
            and other.feats.mood in {mood, Mood.UNKNOWN, None}
        ]
        if not governed:
            return None
        return [f"lemma_in_{family}", "heads_an_imperfect_verb", f"governs_mood={mood}"]

    return when


def _inna_particle(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
    """إنّ and its sisters: accusative on the اسم rather than mood on a verb.

    `conj` is accepted alongside `part` for the reason given in `nawasikh.py`:
    the BERT disambiguator reads إنّ as `conj_sub`, and the lemma is what
    actually identifies the family.
    """
    if token.pos not in {Pos.PART, Pos.CONJ} or not lemma_in(token, INNA_AND_SISTERS):
        return None
    if head is not None:
        return None
    return ["lemma_in_inna_sisters", "sentence_initial", "governs_case=acc"]


JUSSIVE_PARTICLE = Rule(
    id="JUSSIVE_PARTICLE",
    role="حرف جزم",
    priority=40,
    when=_governing_particle(JUSSIVE_PARTICLES, Mood.JUSSIVE, "jussive_particles"),
    description="لم and friends: they put the following imperfect verb in the jussive.",
)

SUBJUNCTIVE_PARTICLE = Rule(
    id="SUBJUNCTIVE_PARTICLE",
    role="حرف نصب",
    priority=40,
    when=_governing_particle(SUBJUNCTIVE_PARTICLES, Mood.SUBJUNCTIVE, "subjunctive_particles"),
    description="لن and friends: they put the following imperfect verb in the subjunctive.",
)

INNA_PARTICLE = Rule(
    id="INNA_PARTICLE",
    role="حرف نصب",
    priority=45,
    when=_inna_particle,
    description="إنّ and its sisters: accusative on the اسم, nominative on the خبر.",
)

PARTICLE_RULES = (JUSSIVE_PARTICLE, SUBJUNCTIVE_PARTICLE, INNA_PARTICLE)
