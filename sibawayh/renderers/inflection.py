"""What to call a word's inflection: مرفوع، منصوب، مجرور، مجزوم.

The middle of an إعراب line names the inflection twice, in two grammatical
shapes. Once as an adjective describing the word, and once as a verbal noun
inside the clause naming the sign:

    مبتدأ **مرفوع** وعلامة **رفع**ه الضمة الظاهرة على آخره

Both come from here, which is why an entry is a pair rather than a string. The
verbal noun also carries the محل clause for an indeclinable word — *في محل
**رفع** فاعل* — so nothing else has to derive one form from the other.

**Where the value comes from, in order.** The role decides when it can: a مفعول
به is منصوب because it is a مفعول به, whatever the analyzer managed to read off
the ending. That mapping is `validate.ROLE_CASE`, imported rather than retyped,
so the sentence shown to the student cannot state a case the validators would
have rejected.

Where the role does not fix a case, `feats` supplies it. صفة is the reason: an
adjective takes the case of the noun it follows, so the role genuinely does not
know it.

Where neither has one there is nothing to say, and `None` is returned. A ماضٍ is
مبني, a حرف has no case at all, and a noun whose case the analyzer could not read
comes back `unknown` — all three are the same answer here, and the caller decides
what to do with the silence.

**Verbs are looked up by role first, and only then by `feats.mood`.** يقرأُ،
يقرأَ and يقرأْ are spelled identically, so morphology reports `mood=unknown` on
almost every undiacritized مضارع. The rule that assigned the role is what
recovered the mood, from the governing particle, so the role is the authority
wherever it states one.

It does not always state one. `خبر — جملة فعلية` names the clause a verb heads
and says nothing about the verb, and يقرأ in الولد يقرأ is a perfectly ordinary
مضارع مرفوع that would otherwise come out with no inflection at all. So the mood
is the second place to look, before the case and for the same reason: it is what
the token itself reports when nothing better is available.
"""

from __future__ import annotations

from dataclasses import dataclass

from sibawayh.schema import Case, Mood
from sibawayh.validate import ROLE_CASE


@dataclass(frozen=True)
class Inflection:
    """One inflection, in the two shapes an إعراب line needs."""

    adjective: str
    """Describes the word: *مبتدأ **مرفوع***."""

    noun: str
    """Names the act, for the sign clause and the محل clause: *وعلامة **رفع**ه*,
    *في محل **رفع** فاعل*."""


CASE_NAME: dict[Case, Inflection] = {
    Case.NOM: Inflection("مرفوع", "رفع"),
    Case.ACC: Inflection("منصوب", "نصب"),
    Case.GEN: Inflection("مجرور", "جر"),
}
"""The three cases. `null` and `unknown` are deliberately absent — a word with no
case and a word whose case we could not read both have no case word to print."""


MOOD_NAME: dict[Mood, Inflection] = {
    Mood.INDICATIVE: Inflection("مرفوع", "رفع"),
    Mood.SUBJUNCTIVE: Inflection("منصوب", "نصب"),
    Mood.JUSSIVE: Inflection("مجزوم", "جزم"),
}
"""The three moods of the مضارع. Two of them share their words with a case —
مرفوع is مرفوع whether it is a noun or a verb — and جزم belongs to verbs alone."""


VERB_ROLE_MOOD: dict[str, Mood] = {
    "فعل مضارع مرفوع": Mood.INDICATIVE,
    "فعل مضارع منصوب": Mood.SUBJUNCTIVE,
    "فعل مضارع مجزوم": Mood.JUSSIVE,
}
"""Which mood each مضارع role asserts.

The role states it in words already, so this reads the mood back out of the role
rather than out of `feats`, where it is usually `unknown`.
"""


ROLE_INFLECTION: dict[str, Inflection] = {
    **{role: CASE_NAME[case] for role, case in ROLE_CASE.items()},
    **{role: MOOD_NAME[mood] for role, mood in VERB_ROLE_MOOD.items()},
}
"""Every role that fixes its own inflection, and what to call it.

Built from `validate.ROLE_CASE` rather than written again, so the renderer cannot
tell a student a case the validators would have refused. Roles absent from it —
صفة, the ماضٍ forms, the حروف — either take their case from `feats` or have none.
"""


def inflection_for(
    role: str | None,
    case: Case | None = None,
    mood: Mood | None = None,
) -> Inflection | None:
    """What to call this word's inflection, or `None` if there is nothing to call.

    Three sources, in order. The role wins where it has an opinion, because a
    role's case is a grammatical fact and a read case is a guess about an ending.
    Then the mood, which carries a verb whose role names its clause rather than
    itself. Then the case, which carries صفة, whose case is the noun's rather
    than the role's.

    A word can have a mood or a case but never both, so the order between the
    last two settles nothing in practice and is only there to be definite.
    """
    if role is not None:
        fixed = ROLE_INFLECTION.get(role)
        if fixed is not None:
            return fixed
    if mood is not None:
        named = MOOD_NAME.get(mood)
        if named is not None:
            return named
    if case is None:
        return None
    return CASE_NAME.get(case)
