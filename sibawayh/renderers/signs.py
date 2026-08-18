"""The علامة — which mark or letter carries the case, and why.

This is the clause that closes an إعراب line, and it is the part a naive
template gets wrong:

    الكِتابُ: مبتدأ مرفوع وعلامة رفعه **الضمة الظاهرة على آخره**
    العِراقِيِّينَ: اسم إنّ منصوب وعلامة نصبه **الياء لأنه جمع مذكر سالم**

The sign is not fixed by the case. It depends on how the word declines, and a
template that always printed الفتحة for an accusative would state something false
about العراقيين with full confidence.

**Two classes are implemented, because two are what the eval set contains.** Of
its forty gold tokens, thirty-eight decline with visible harakat and two are
جمع مذكر سالم. المثنى، جمع المؤنث السالم، الأسماء الخمسة، الممنوع من الصرف and
المقصور have no gold token anywhere in it, and a class with nothing to check it
against is a guess wearing a grammatical term — the same argument that left the
rule engine at 26 rules instead of the plan's forty. They arrive with the
sentences that test them.

`declension_of` returns `None` for everything it does not recognise, and the
caller then prints the role and the case and stops. `الكِتابانِ: مبتدأ مرفوع` is
thin but true; `وعلامة رفعه الضمة` would be false.

**Detecting جمع مذكر سالم needs the lemma, not the ending.** مَساكين ends in ـين
and is `num=p, gen=m`, and it is جمع تكسير, which takes ordinary harakat. What
separates them is that a sound plural is its own singular plus the suffix:
عِراقِيّ + ين، قادِر + ون. مَسْكين + ين is not مَساكين, so it fails and abstains.
A منقوص sound plural like مُحامون fails it too and also abstains, which is the
right outcome for a class this table has not been taught.

**The alef of tanween is not a final alef.** رائِعاً ends in ا, and an ending-based
rule would call it مقصور and refuse to name its sign. The ا carries a tanween
fath and belongs to the vowelling, not to the word, so it is dropped before the
ending is read.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sibawayh.diacritics import Marked, split_marks
from sibawayh.renderers.inflection import CASE_NAME, MOOD_NAME, Inflection
from sibawayh.schema import Case, Gender, Mood, Number, Token

TANWEEN_FATH = "ً"
SHADDA = "ّ"

INDECLINABLE_ENDINGS = frozenset("اىو")
"""Endings whose case cannot appear on them — المقصور، المعتل الآخر، الأسماء
الخمسة. The sign there is مقدرة, and naming which vowel is *notionally* there is
a separate table that no gold token needs yet."""

SOUND_PLURAL_SUFFIXES = ("ون", "ين")


class Declension(StrEnum):
    """How a word carries its case."""

    SOUND = "sound"
    """بالحركات الظاهرة — the ordinary case, and 38 of the eval set's 40 tokens."""

    MASCULINE_PLURAL = "masculine_plural"
    """جمع مذكر سالم — the case rides on a letter, الواو or الياء, not a harakat."""


@dataclass(frozen=True)
class Sign:
    """The words naming a case's sign, ready to follow *وعلامة رفعه*."""

    text: str
    """The whole clause: *الضمة الظاهرة على آخره*."""

    mark: str
    """The mark or letter alone: *الضمة*.

    Held separately rather than sliced off `text`, because it is what a model's
    rewrite of this line has to be checked against, and a check that depends on
    where the spaces fall is a check that will one day pass for the wrong reason.
    """


SIGN: dict[Declension, dict[Inflection, Sign]] = {
    Declension.SOUND: {
        CASE_NAME[Case.NOM]: Sign("الضمة الظاهرة على آخره", "الضمة"),
        CASE_NAME[Case.ACC]: Sign("الفتحة الظاهرة على آخره", "الفتحة"),
        CASE_NAME[Case.GEN]: Sign("الكسرة الظاهرة على آخره", "الكسرة"),
        MOOD_NAME[Mood.JUSSIVE]: Sign("السكون", "السكون"),
    },
    Declension.MASCULINE_PLURAL: {
        CASE_NAME[Case.NOM]: Sign("الواو لأنه جمع مذكر سالم", "الواو"),
        CASE_NAME[Case.ACC]: Sign("الياء لأنه جمع مذكر سالم", "الياء"),
        CASE_NAME[Case.GEN]: Sign("الياء لأنه جمع مذكر سالم", "الياء"),
    },
}
"""Every sign this table is willing to name.

Keyed on the `Inflection` from `inflection.py` rather than on a case, because a
مرفوع noun and a مرفوع verb take the same sign and the two arrive as the same
value. المجزوم appears only under `SOUND`: a جمع مذكر سالم is a noun and has no
mood, so the missing entry is a fact about Arabic and not an omission.
"""


def _drop_tanween_alef(marked: Marked) -> Marked:
    """Remove a final alef that only carries a tanween fath.

    رائِعاً is not a word ending in alef. The alef is part of how the fatha
    tanween is written, and reading it as the word's last letter would make an
    ordinary accusative noun look مقصور.
    """
    if len(marked) > 1:
        base, marks = marked[-1]
        if base == "ا" and TANWEEN_FATH in marks:
            return marked[:-1]
    return marked


def _bare(text: str) -> str:
    """The letters of `text` with every mark removed."""
    return "".join(base for base, _ in split_marks(text))


def _is_sound_masculine_plural(token: Token, ending: str) -> bool:
    """Whether `token` is its own singular plus ون or ين.

    The lemma is what makes this safe. مَساكين ends in ـين and is a masculine
    plural, but مَسْكين + ين is not مَساكين, so it is recognised as the جمع تكسير
    it is and gets ordinary harakat.
    """
    if not token.lemma:
        return False
    return _bare(token.diac or token.form).endswith(_bare(token.lemma) + ending)


def declension_of(token: Token) -> Declension | None:
    """How `token` carries its case, or `None` where this table cannot say.

    `None` is not a failure. It is the answer for المثنى، جمع المؤنث السالم،
    المقصور and every other class with no gold token to check it against, and it
    tells the caller to state the case and stop rather than name a sign it cannot
    justify.
    """
    marked = _drop_tanween_alef(split_marks(token.diac or token.form))
    if not marked:
        return None

    last_base, last_marks = marked[-1]
    if last_base in INDECLINABLE_ENDINGS:
        return None
    if last_base == "ي" and SHADDA not in last_marks:
        return None

    number, gender = token.feats.num, token.feats.gen
    if number is Number.D or number is Number.UNKNOWN:
        return None

    if number is Number.P:
        bare = _bare(token.diac or token.form)
        if gender is Gender.M:
            for ending in SOUND_PLURAL_SUFFIXES:
                if bare.endswith(ending):
                    return (
                        Declension.MASCULINE_PLURAL
                        if _is_sound_masculine_plural(token, ending)
                        else None
                    )
        elif gender is Gender.F and bare.endswith("ات"):
            return None

    return Declension.SOUND


def sign_for(token: Token, inflection: Inflection) -> Sign | None:
    """The sign `token` carries for `inflection`, or `None` if it cannot be named."""
    declension = declension_of(token)
    if declension is None:
        return None
    return SIGN[declension].get(inflection)
