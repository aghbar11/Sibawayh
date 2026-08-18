"""Tests for using the diacritics the student typed.

The module half is string logic and needs no model. The wiring half drives
`tests/data/camel_analyses.json` — real recorded CAMeL output — because the
whole point of the feature is choosing among readings CAMeL actually returns,
and a hand-built candidate list would prove nothing about that.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sibawayh.diacritics import compatible, has_diacritics, rank, split_marks
from sibawayh.morphology import MorphologyError, sentence_from_analyses, tokens_from_word
from sibawayh.schema import Voice

REPO_ROOT = Path(__file__).resolve().parents[1]
RECORDED = json.loads(
    (REPO_ROOT / "tests" / "data" / "camel_analyses.json").read_text(encoding="utf-8")
)["sentences"]

FATHA = "َ"
DAMMA = "ُ"
KASRA = "ِ"
SUKUN = "ْ"
SHADDA = "ّ"


def words_of(sentence_id: str) -> list[tuple[str, list[tuple[dict[str, Any], float]]]]:
    return [
        (word["word"], [(a["analysis"], a["score"]) for a in word["analyses"]])
        for word in RECORDED[sentence_id]["words"]
    ]


# --- reading a word as letters and marks --------------------------------------------


def test_marks_attach_to_the_letter_before_them() -> None:
    assert split_marks("كَتَبَ") == (
        ("ك", frozenset({FATHA})),
        ("ت", frozenset({FATHA})),
        ("ب", frozenset({FATHA})),
    )


def test_a_letter_may_carry_more_than_one_mark() -> None:
    """Shadda and a vowel sit on the same letter."""
    assert split_marks("رّ" + FATHA) == (("ر", frozenset({SHADDA, FATHA})),)


def test_a_bare_word_has_no_marks_at_all() -> None:
    assert split_marks("كتب") == (("ك", frozenset()), ("ت", frozenset()), ("ب", frozenset()))


def test_a_mark_with_no_letter_to_sit_on_is_dropped() -> None:
    """Malformed input, not a crash."""
    assert split_marks(FATHA + "ك") == (("ك", frozenset()),)


def test_split_marks_normalizes_first() -> None:
    """Tatweel is noise, and must not make two spellings of one word disagree."""
    assert split_marks("كـتب") == split_marks("كتب")


def test_has_diacritics() -> None:
    assert has_diacritics("كُتِبَت")
    assert not has_diacritics("كتبت")
    assert not has_diacritics("")


# --- compatibility ------------------------------------------------------------------


def test_a_word_is_compatible_with_itself() -> None:
    assert compatible("كُتِبَت", "كُتِبَت")


def test_a_bare_typed_word_is_compatible_with_everything() -> None:
    """A student who marked nothing has told us nothing, and must not narrow
    the field. This is the ordinary case and the reason nothing changes for
    input that carries no diacritics."""
    assert compatible("كتبت", "كَتَبَت")
    assert compatible("كتبت", "كُتِبَت")


def test_partial_vowelling_is_enough() -> None:
    """Students mark the ending, or the one letter they are unsure of."""
    assert compatible("كُتِبت", "كُتِبَت")
    assert not compatible("كُتِبت", "كَتَبَت")


def test_a_contradicted_mark_rules_a_reading_out() -> None:
    """The whole point: كُتِبَت is passive, كَتَبَت is active, and the first
    letter's vowel is the entire difference."""
    assert not compatible("كُتِبَتْ", "كَتَبَت")
    assert compatible("كُتِبَتْ", "كُتِبَت")


def test_a_mark_the_candidate_leaves_open_does_not_contradict_it() -> None:
    """CAMeL writes كُتِبَت with no final sukun; a student writing كُتِبَتْ is not
    disagreeing with it, only being more specific."""
    assert compatible("كتبتْ", "كُتِبَت")


def test_a_different_word_is_never_compatible() -> None:
    assert not compatible("كَتَبَ", "قَرَأَ")
    assert not compatible("كَتَبَ", "كَتَبَت")


def test_shadda_is_a_mark_like_any_other() -> None:
    assert compatible("يَقْرَأ", "يَقْرَأ")
    assert not compatible("يَقْرَأ", "يَقَرّا")


# --- ranking ------------------------------------------------------------------------


def test_no_typed_diacritics_leaves_the_order_alone() -> None:
    ranking = rank("كتبت", ["كَتَبَت", "كُتِبَت"])
    assert ranking.order == (0, 1)
    assert not ranking.decided


def test_a_matching_reading_is_promoted() -> None:
    ranking = rank("كُتِبَتْ", ["كَتَبَت", "كُتِبَت", "كَتَبْتِ"])
    assert ranking.order[0] == 1
    assert ranking.matched == (1,)
    assert ranking.decided


def test_rejected_readings_are_kept_not_dropped() -> None:
    """A rejected reading is still a reading, and the confidence layer wants to
    see how close the field was."""
    ranking = rank("كُتِبَتْ", ["كَتَبَت", "كُتِبَت", "كَتَبْتِ"])
    assert sorted(ranking.order) == [0, 1, 2]
    assert ranking.order == (1, 0, 2)


def test_ties_keep_the_disambiguator_order() -> None:
    ranking = rank("كُتِبَت", ["كُتِبَت", "كُتِبَت"])
    assert ranking.order == (0, 1)
    assert not ranking.decided


def test_a_vowelling_that_matches_nothing_changes_nothing() -> None:
    """We do not recognise what was typed. Reordering on that basis would be a
    guess, and the honest response is to leave CAMeL's ranking alone."""
    ranking = rank("كِتِبِتِ", ["كَتَبَت", "كُتِبَت"])
    assert ranking.order == (0, 1)
    assert not ranking.decided


def test_an_unvowelled_candidate_never_counts_as_a_match() -> None:
    """CAMeL's backoff analysis echoes the surface back with no vowelling. It is
    compatible with everything by construction, so without this it would outrank
    the real readings — which is how الدرس lost its features and came back as a
    backoff token."""
    ranking = rank("الدَّرْسَ", ["الدَرْسَ", "الدرس"])
    assert ranking.matched == ()
    assert ranking.order == (0, 1)


def test_ranking_of_nothing() -> None:
    assert rank("كُتِبَت", []).order == ()


# --- wired into the morphology stage ------------------------------------------------


def test_the_passive_is_recovered_when_the_student_vowels_it() -> None:
    """`verbal_passive_01` — the sentence the pipeline gets wrong. CAMeL ranks
    the active reading first at 1.0 and buries the passive at 0.9283, in a
    cluster of runners-up it cannot separate; the student's vowelling settles
    which member of that cluster was meant."""
    word, analyses = words_of("verbal_passive_01")[0]

    bare = tokens_from_word(word, analyses)[0]
    assert bare.feats.voice is Voice.ACTIVE

    vowelled = tokens_from_word(word, analyses, typed="كُتِبَتْ")[0]
    assert vowelled.feats.voice is Voice.PASSIVE
    assert vowelled.diac == "كُتِبَت"


def test_the_reordering_is_recorded_as_evidence() -> None:
    word, analyses = words_of("verbal_passive_01")[0]
    token = tokens_from_word(word, analyses, typed="كُتِبَتْ")[0]
    assert "typed_diacritics_chose_this_reading" in token.evidence


def test_nothing_is_recorded_when_the_diacritics_decided_nothing() -> None:
    word, analyses = words_of("verbal_passive_01")[0]
    assert tokens_from_word(word, analyses)[0].evidence == []
    assert tokens_from_word(word, analyses, typed="كتبت")[0].evidence == []


def test_the_rejected_readings_stay_in_alternatives() -> None:
    word, analyses = words_of("verbal_passive_01")[0]
    token = tokens_from_word(word, analyses, typed="كُتِبَتْ")[0]
    assert len(token.alternatives) == len(analyses) - 1
    assert any(alt.feats.voice is Voice.ACTIVE for alt in token.alternatives)


def test_typed_forms_are_matched_to_words_one_for_one() -> None:
    record = RECORDED["verbal_passive_01"]
    sentence = sentence_from_analyses(
        record["text"], words_of("verbal_passive_01"), typed=["كُتِبَتْ", "المَقالَةُ"]
    )
    assert sentence.tokens[0].feats.voice is Voice.PASSIVE
    assert sentence.tokens[1].diac == "المَقالَةُ"


def test_a_typed_list_of_the_wrong_length_is_refused() -> None:
    """Silently misaligning them would attribute one word's vowels to another."""
    record = RECORDED["verbal_passive_01"]
    with pytest.raises(MorphologyError, match="typed words"):
        sentence_from_analyses(record["text"], words_of("verbal_passive_01"), typed=["كُتِبَتْ"])


def test_omitting_the_typed_forms_changes_nothing() -> None:
    record = RECORDED["verbal_passive_01"]
    without = sentence_from_analyses(record["text"], words_of("verbal_passive_01"))
    bare = sentence_from_analyses(
        record["text"], words_of("verbal_passive_01"), typed=["كتبت", "المقالة"]
    )
    assert without.model_dump() == bare.model_dump()
