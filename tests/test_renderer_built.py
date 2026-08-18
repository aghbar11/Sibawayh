"""Tests for what a مبني word's line says instead of a case.

The perfect verb is the whole difficulty. كُتِبَتْ and كَتَبْتُ end in the same
letter and are built on opposite things, so most of these tests are about telling
those apart rather than about the vowels, which are read straight off the word.
"""

from __future__ import annotations

import json
from pathlib import Path

from sibawayh.renderers.built import NO_PLACE, built_on, is_built, place_of
from sibawayh.renderers.inflection import CASE_NAME, inflection_for
from sibawayh.renderers.phrases import phrase_for
from sibawayh.schema import (
    Aspect,
    Case,
    Features,
    Gender,
    Number,
    Person,
    Pos,
    Sentence,
    Token,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))
GOLD = [Sentence.model_validate(record) for record in EVAL["sentences"]]


def word(diac: str, pos: Pos, **feats: object) -> Token:
    return Token(id=1, form=diac, diac=diac, pos=pos, feats=Features(**feats))  # type: ignore[arg-type]


def past(diac: str, person: Person = Person.THIRD, **feats: object) -> Token:
    return word(diac, Pos.VERB, aspect=Aspect.PERFECT, person=person, **feats)


# --- which words are مبني at all ----------------------------------------------------


def test_particles_and_pronouns_are_built() -> None:
    assert is_built(word("إِنَّ", Pos.PART))
    assert is_built(word("في", Pos.PREP))
    assert is_built(word("هُوَ", Pos.PRON))


def test_nouns_and_adjectives_are_not() -> None:
    assert not is_built(word("الكِتابُ", Pos.NOUN))
    assert not is_built(word("الجَديدُ", Pos.ADJ))


def test_the_perfect_is_built_and_the_imperfect_is_not() -> None:
    """This is the difference that makes لم يقرأْ a جزم rather than a coincidence."""
    assert is_built(past("كَتَبَ"))
    assert not is_built(word("يَقْرَأُ", Pos.VERB, aspect=Aspect.IMPERFECT))


# --- what it is built on ------------------------------------------------------------


def test_the_final_vowel_names_it() -> None:
    assert built_on(word("إِنَّ", Pos.PART)) == "الفتح"
    assert built_on(word("هُوَ", Pos.PRON)) == "الفتح"
    assert built_on(word("لَمْ", Pos.PART)) == "السكون"


def test_an_unmarked_ending_is_silent() -> None:
    """CAMeL writes في with no final mark, and a missing vowel is a sukun."""
    assert built_on(word("في", Pos.PREP)) == "السكون"


def test_a_declinable_word_is_built_on_nothing() -> None:
    assert built_on(word("الكِتابُ", Pos.NOUN)) is None
    assert built_on(word("يَقْرَأُ", Pos.VERB, aspect=Aspect.IMPERFECT)) is None


def test_a_covert_pronoun_is_built_on_nothing() -> None:
    """It was never written, so there is no ending to be built on. Its line says
    تقديره هو rather than مبني على."""
    covert = Token(id=1, form="هو", diac="هُوَ", pos=Pos.PRON, inserted=True)
    assert built_on(covert) is None


# --- the perfect verb ---------------------------------------------------------------


def test_a_bare_perfect_is_built_on_the_fatha() -> None:
    assert built_on(past("كَتَبَ")) == "الفتح"


def test_the_silent_feminine_ta_does_not_change_it() -> None:
    """كُتِبَتْ ends in a silent ت, and reading the last mark would say السكون. The
    ت is a suffix; the verb ends at the ب underneath it and stays على الفتح. This
    is `verbal_passive_01`, not a hypothetical."""
    assert built_on(past("كُتِبَتْ")) == "الفتح"
    assert built_on(past("كُتِبَت")) == "الفتح"


def test_the_subject_ta_does_change_it() -> None:
    """Same last letter, opposite answer. Here the ت is تاء الفاعل and the verb
    was silenced to receive it. Person is what tells them apart."""
    assert built_on(past("كَتَبْتُ", Person.FIRST)) == "السكون"
    assert built_on(past("كَتَبْتَ", Person.SECOND)) == "السكون"
    assert built_on(past("كَتَبْنا", Person.FIRST, num=Number.P)) == "السكون"


def test_the_ending_is_only_measured_when_no_person_is_reported() -> None:
    """The fallback, and the reason it tests for a vowel rather than for a
    suffix: تاء الفاعل and تاء التأنيث are the same letter, and the only
    difference between them is that one is متحركة."""
    assert built_on(past("كَتَبْتُ", Person.NULL)) == "السكون"
    assert built_on(past("كُتِبَتْ", Person.NULL)) == "الفتح"


def test_the_plural_waw_raises_it() -> None:
    assert built_on(past("كَتَبوا", num=Number.P)) == "الضم"


def test_the_nun_of_the_feminine_silences_it() -> None:
    """Third person like تاء التأنيث, but the opposite answer, so it is checked
    before the person is."""
    assert built_on(past("كَتَبْنَ", num=Number.P, gen=Gender.F)) == "السكون"


# --- the محل clause -----------------------------------------------------------------


def test_a_word_filling_a_slot_with_a_case_has_a_place() -> None:
    """A covert فاعل is مرفوع as a matter of grammar even though nothing on it
    could show it."""
    assert place_of(CASE_NAME[Case.NOM], "فاعل") == "في محل رفع فاعل"


def test_a_particle_fills_no_such_slot() -> None:
    assert place_of(None, "حرف نصب") == NO_PLACE


def test_a_case_with_no_role_to_attach_it_to_says_nothing() -> None:
    """It would read as a fragment."""
    assert place_of(CASE_NAME[Case.NOM], None) == NO_PLACE


# --- against the eval set -----------------------------------------------------------


def test_every_built_token_of_the_eval_set_is_named() -> None:
    unnamed = [
        (sentence.id, token.form)
        for sentence in GOLD
        for token in sentence.tokens
        if is_built(token) and not token.inserted and built_on(token) is None
    ]
    assert not unnamed


def test_the_built_tokens_of_the_eval_set_are_what_we_think() -> None:
    built = {
        token.form: built_on(token)
        for sentence in GOLD
        for token in sentence.tokens
        if is_built(token) and not token.inserted
    }
    assert built == {
        "كتب": "الفتح",
        "كتبت": "الفتح",
        "في": "السكون",
        "كان": "الفتح",
        "إن": "الفتح",
        "لم": "السكون",
        "لن": "السكون",
    }


def test_the_particles_of_the_eval_set_have_no_place_and_the_covert_agent_does() -> None:
    places = {}
    for sentence in GOLD:
        for token in sentence.tokens:
            if not is_built(token):
                continue
            phrase = phrase_for(token.irab_role) if token.irab_role else None
            inflection = inflection_for(token.irab_role, token.feats.case, token.feats.mood)
            places[token.form] = place_of(inflection, phrase.head if phrase else None)

    assert places["إن"] == NO_PLACE
    assert places["في"] == NO_PLACE
    assert places["كتب"] == NO_PLACE
    assert places["هو*"] == "في محل رفع فاعل"
