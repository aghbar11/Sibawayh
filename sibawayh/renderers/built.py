"""المبني — words that have no case, and what an إعراب line says about them instead.

A معرب word changes its ending to show its role: الكِتابُ، الكِتابَ، الكِتابِ. A
مبني word does not. إنّ is إنّ wherever it stands, so the line cannot say منصوب,
and says two other things in its place:

    إِنَّ: حرف نصب **مبني على الفتح** **لا محل له من الإعراب**
    هو:   ضمير **مبني على الفتح** **في محل رفع فاعل**

**What it is built on** is read off the word's own last vowel. The ending never
changes, so whatever mark CAMeL's `diac` puts there is the answer — لَمْ is built
على السكون, إِنَّ على الفتح.

**Whether it has a محل** is decided by the role, not by the word. A word can be
مبني and still be filling a slot that has a case: a covert فاعل is مرفوع as a
matter of grammar even though nothing on it could show it, and that is what في
محل رفع فاعل says. A حرف is not filling such a slot at all, and gets لا محل له
من الإعراب. So the test is simply whether `inflection_for` found a case for the
role — the same call the معرب path makes, used here for a different purpose.

**The perfect verb is the one that cannot be read off the ending.** كُتِبَتْ ends
in a silent ت and is مبني على الفتح: the ت is تاء التأنيث الساكنة, a suffix, and
the verb ends at the ب underneath it. كَتَبْتُ ends in the same letter and *is*
مبني على السكون, because there the ت is تاء الفاعل and the verb was made silent
to receive it. Same letter, opposite answers. This is not hypothetical — كتبت is
`verbal_passive_01`.

What separates them is *who is speaking*, so `person` decides it and not the
spelling. تاء الفاعل is first or second person; تاء التأنيث is third. That is a
feature CAMeL reports on every perfect verb, and it is right even where the
writing is bare. Only if no person is reported does the ending get measured, and
then the test is whether the ت carries a vowel — because the whole difference
between the two is that one is متحركة and one is ساكنة, which means comparing
suffixes letter by letter answers nothing.

**A covert pronoun is not built on anything.** It was never written, so there is
no ending to be built on. Its line is *ضمير مستتر تقديره هو*, and `built_on`
returns `None` for it — the caller says تقديره instead of مبني على.
"""

from __future__ import annotations

from sibawayh.diacritics import split_marks
from sibawayh.renderers.inflection import Inflection
from sibawayh.schema import Aspect, Gender, Number, Person, Pos, Token

FATHA = "َ"
DAMMA = "ُ"
KASRA = "ِ"
SUKUN = "ْ"

VOWEL_NAME = {FATHA: "الفتح", DAMMA: "الضم", KASRA: "الكسر", SUKUN: "السكون"}
"""What each final vowel is called in a مبني على clause. An unmarked ending is
silent, so it reads as السكون too."""

BUILT_POS = frozenset({Pos.PART, Pos.PREP, Pos.CONJ, Pos.PRON})
"""Parts of speech that are مبني whatever they are doing.

Nouns and adjectives are معرب. Verbs are split — see `is_built`.
"""

NO_PLACE = "لا محل له من الإعراب"
"""What is said of a مبني word that fills no slot with a case: every حرف, and
every ماضٍ."""

PLURAL_WAW = "وا"
"""واو الجماعة. A ماضٍ carrying it is مبني على الضم."""

FEMININE_NUN = "ن"
"""نون النسوة. Third person like تاء التأنيث, but it silences the verb rather
than leaving it على الفتح, so it is checked before the person is."""

MOVING_VOWELS = frozenset({FATHA, DAMMA, KASRA})
"""What makes a ضمير رفع متحرك متحرك. Only reached when no person is reported."""


def is_built(token: Token) -> bool:
    """Whether `token` is مبني — has an ending that never changes.

    Verbs split. The ماضٍ and the أمر are مبني; the مضارع is معرب, which is what
    makes لم يقرأْ a جزم rather than a coincidence.
    """
    if token.pos in BUILT_POS:
        return True
    if token.pos is Pos.VERB:
        return token.feats.aspect in (Aspect.PERFECT, Aspect.IMPERATIVE)
    return False


def _perfect_verb_built_on(token: Token) -> str:
    """What a ماضٍ is built on, decided by what is attached to it.

    واو الجماعة raises it to الضم. نون النسوة and any ضمير رفع متحرك silence it.
    Everything else — a bare verb, or one carrying تاء التأنيث الساكنة — leaves it
    على الفتح.

    `person` is what tells تاء الفاعل from تاء التأنيث, and it is checked before
    the spelling because the two are spelled alike. The ending is measured only
    when no person was reported.
    """
    marked = split_marks(token.diac or token.form)
    bare = "".join(base for base, _ in marked)

    if bare.endswith(PLURAL_WAW):
        return "الضم"
    if bare.endswith(FEMININE_NUN) and token.feats.num is Number.P and token.feats.gen is Gender.F:
        return "السكون"

    person = token.feats.person
    if person in (Person.FIRST, Person.SECOND):
        return "السكون"
    if person is Person.THIRD:
        return "الفتح"

    if marked and marked[-1][0] == "ت":
        return "السكون" if marked[-1][1] & MOVING_VOWELS else "الفتح"
    if bare.endswith("نا"):
        return "السكون"
    return "الفتح"


def built_on(token: Token) -> str | None:
    """What `token` is built on — الفتح، الضم، الكسر، السكون — or `None`.

    `None` means there is nothing to be built on rather than that the answer is
    unknown: the token is معرب, or it is a covert pronoun that was never written.
    """
    if not is_built(token) or token.inserted:
        return None

    if token.pos is Pos.VERB and token.feats.aspect is Aspect.PERFECT:
        return _perfect_verb_built_on(token)

    marked = split_marks(token.diac or token.form)
    if not marked:
        return None
    _, marks = marked[-1]
    for vowel, name in VOWEL_NAME.items():
        if vowel in marks:
            return name
    return "السكون"


def place_of(inflection: Inflection | None, head: str | None) -> str:
    """The محل clause: *في محل رفع فاعل*, or *لا محل له من الإعراب*.

    A مبني word still occupies a slot, and the slot may have a case even though
    the word cannot show it. `inflection` is that case, already worked out for
    the role; `head` is what the slot is called. Both are needed — a case with no
    role to attach it to would read as a fragment — and without them the word is
    filling no such slot and the line says so.
    """
    if inflection is None or head is None:
        return NO_PLACE
    return f"في محل {inflection.noun} {head}"
