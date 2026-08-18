"""Tests for naming the sign of a case.

Driven off the eval set where it can be, because that is the only place a claim
about Arabic here can be checked rather than asserted. The two classes this table
knows are the two the eval set contains; everything else has to abstain, and most
of these tests are about the abstaining.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sibawayh.renderers.inflection import CASE_NAME, MOOD_NAME, inflection_for
from sibawayh.renderers.signs import Declension, Sign, declension_of, sign_for
from sibawayh.schema import Case, Features, Gender, Mood, Number, Pos, Sentence, Token

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))
GOLD = [Sentence.model_validate(record) for record in EVAL["sentences"]]


def noun(diac: str, *, lemma: str = "", num: Number = Number.S, gen: Gender = Gender.M) -> Token:
    return Token(
        id=1,
        form=diac,
        diac=diac,
        lemma=lemma or diac,
        pos=Pos.NOUN,
        feats=Features(num=num, gen=gen),
    )


# --- the ordinary case --------------------------------------------------------------


def test_a_singular_noun_declines_with_harakat() -> None:
    assert declension_of(noun("الكِتابُ")) is Declension.SOUND


def test_the_three_harakat() -> None:
    word = noun("الكِتابُ")
    assert sign_for(word, CASE_NAME[Case.NOM]) == Sign("الضمة الظاهرة على آخره", "الضمة")
    assert sign_for(word, CASE_NAME[Case.ACC]) == Sign("الفتحة الظاهرة على آخره", "الفتحة")
    assert sign_for(word, CASE_NAME[Case.GEN]) == Sign("الكسرة الظاهرة على آخره", "الكسرة")


def test_a_jussive_verb_is_signed_by_a_sukun() -> None:
    verb = Token(id=1, form="يَكْتُبْ", diac="يَكْتُبْ", pos=Pos.VERB, feats=Features(num=Number.S))
    assert sign_for(verb, MOOD_NAME[Mood.JUSSIVE]) == Sign("السكون", "السكون")


def test_a_broken_plural_declines_like_a_singular() -> None:
    """رِجال is جمع تكسير: plural in meaning, ordinary harakat in form."""
    assert declension_of(noun("رِجالٌ", lemma="رَجُل", num=Number.P)) is Declension.SOUND


# --- جمع مذكر سالم ------------------------------------------------------------------


def test_the_sound_masculine_plural_is_recognised() -> None:
    plural = noun("العِراقِيِّينَ", lemma="عِراقِيّ", num=Number.P)
    assert declension_of(plural) is Declension.MASCULINE_PLURAL


def test_it_takes_a_letter_and_says_why() -> None:
    """The whole reason this table exists. A template that always printed الفتحة
    for an accusative would be confidently wrong about this word."""
    plural = noun("العِراقِيِّينَ", lemma="عِراقِيّ", num=Number.P)
    assert sign_for(plural, CASE_NAME[Case.ACC]) == Sign("الياء لأنه جمع مذكر سالم", "الياء")
    assert sign_for(plural, CASE_NAME[Case.GEN]) == Sign("الياء لأنه جمع مذكر سالم", "الياء")

    nominative = noun("قادِرونَ", lemma="قادِر", num=Number.P)
    assert sign_for(nominative, CASE_NAME[Case.NOM]) == Sign("الواو لأنه جمع مذكر سالم", "الواو")


def test_a_plural_noun_has_no_mood_to_be_signed_for() -> None:
    plural = noun("قادِرونَ", lemma="قادِر", num=Number.P)
    assert sign_for(plural, MOOD_NAME[Mood.JUSSIVE]) is None


def test_a_broken_plural_ending_in_the_same_letters_is_not_fooled() -> None:
    """مَساكين ends in ـين and is `num=p, gen=m`, and it is جمع تكسير. The lemma
    is what separates them: مَسْكين + ين is not مَساكين."""
    assert declension_of(noun("مَساكينَ", lemma="مِسْكين", num=Number.P)) is None


def test_a_sound_plural_with_no_lemma_to_check_against_abstains() -> None:
    token = Token(
        id=1, form="قادرون", diac="قادِرونَ", pos=Pos.NOUN, feats=Features(num=Number.P, gen=Gender.M)
    )
    assert declension_of(token) is None


# --- what it refuses to say ---------------------------------------------------------


def test_the_dual_abstains() -> None:
    """المثنى takes الألف and الياء, and no gold token tests it."""
    assert declension_of(noun("الكِتابانِ", lemma="كِتاب", num=Number.D)) is None


def test_the_sound_feminine_plural_abstains() -> None:
    """جمع المؤنث السالم takes الكسرة where a singular takes الفتحة, so treating
    it as ordinary would be wrong in the accusative specifically."""
    assert declension_of(noun("المُعَلِّماتُ", lemma="مُعَلِّمة", num=Number.P, gen=Gender.F)) is None


def test_a_word_ending_in_alef_maqsura_abstains() -> None:
    """المقصور carries its case notionally; there is no visible sign to name."""
    assert declension_of(noun("الفَتى", lemma="فَتى")) is None


def test_a_defective_noun_abstains() -> None:
    """المنقوص — القاضي shows nothing in the nominative or the genitive."""
    assert declension_of(noun("القاضي", lemma="قاضي")) is None


def test_a_nisba_ending_in_a_doubled_ya_is_not_defective() -> None:
    """عِراقِيّ ends in ي too, but the shadda makes it an ordinary noun that shows
    its harakat."""
    assert declension_of(noun("العِراقِيُّ", lemma="عِراقِيّ")) is Declension.SOUND


def test_an_unreadable_number_abstains() -> None:
    """It might be a dual, and a dual takes a different sign."""
    assert declension_of(noun("الكِتاب", lemma="كِتاب", num=Number.UNKNOWN)) is None


def test_an_empty_word_abstains() -> None:
    assert declension_of(Token(id=1, form="ـ", diac="ـ", pos=Pos.NOUN)) is None


# --- the trap the eval set actually contains ----------------------------------------


def test_the_alef_of_tanween_is_not_a_final_alef() -> None:
    """رائِعاً ends in ا on the page, but the alef belongs to the tanween rather
    than to the word. Read as an ending it would look مقصور, and an ordinary
    accusative noun would lose its sign."""
    word = noun("رائِعاً", lemma="رائِع")
    assert declension_of(word) is Declension.SOUND
    assert sign_for(word, CASE_NAME[Case.ACC]) == Sign("الفتحة الظاهرة على آخره", "الفتحة")


def test_a_word_that_is_only_an_alef_is_left_alone() -> None:
    assert declension_of(noun("ا")) is None


# --- against the eval set -----------------------------------------------------------


def test_every_gold_token_with_a_case_gets_a_sign() -> None:
    """No token of the eval set falls through to abstention. If one starts to,
    this table has lost something it used to know."""
    missing = []
    for sentence in GOLD:
        for token in sentence.tokens:
            inflection = inflection_for(token.irab_role, token.feats.case)
            if inflection is None:
                continue
            if sign_for(token, inflection) is None:
                missing.append((sentence.id, token.form))
    assert not missing


def test_the_two_sound_plurals_of_the_eval_set_are_the_only_ones() -> None:
    plurals = [
        token.form
        for sentence in GOLD
        for token in sentence.tokens
        if declension_of(token) is Declension.MASCULINE_PLURAL
    ]
    assert sorted(plurals) == ["العراقيين", "قادرون"]


def test_signs_are_frozen() -> None:
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        Sign("الضمة", "الضمة").text = "الفتحة"  # type: ignore[misc]
