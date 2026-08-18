"""Tests for naming a word's inflection.

Two things are being pinned. That the renderer agrees with the validators about
which case a role takes -- the table is imported from `validate`, and a test
holds it there -- and that silence is returned rather than a guess wherever
neither the role nor the morphology knows.
"""

from __future__ import annotations

import pytest
from sibawayh.renderers.inflection import (
    CASE_NAME,
    MOOD_NAME,
    ROLE_INFLECTION,
    Inflection,
    inflection_for,
)
from sibawayh.schema import Case, Mood
from sibawayh.validate import ROLE_CASE, ROLES

# --- the words ----------------------------------------------------------------------


def test_each_case_has_both_shapes() -> None:
    """An i'rab line says the inflection twice: مبتدأ مرفوع وعلامة رفعه."""
    assert CASE_NAME[Case.NOM] == Inflection("مرفوع", "رفع")
    assert CASE_NAME[Case.ACC] == Inflection("منصوب", "نصب")
    assert CASE_NAME[Case.GEN] == Inflection("مجرور", "جر")


def test_an_unreadable_case_has_no_name() -> None:
    """`unknown` is a failure to read the ending, and `null` is a word with no
    case. Neither has a word to print, and inventing one is the failure mode the
    whole project abstains to avoid."""
    assert Case.UNKNOWN not in CASE_NAME
    assert Case.NULL not in CASE_NAME


def test_the_jussive_is_the_one_mood_with_its_own_words() -> None:
    assert MOOD_NAME[Mood.JUSSIVE] == Inflection("مجزوم", "جزم")
    assert MOOD_NAME[Mood.INDICATIVE] == CASE_NAME[Case.NOM]
    assert MOOD_NAME[Mood.SUBJUNCTIVE] == CASE_NAME[Case.ACC]


# --- agreement with the validators --------------------------------------------------


def test_every_role_the_validators_fix_a_case_for_is_named() -> None:
    assert set(ROLE_CASE) <= set(ROLE_INFLECTION)


def test_the_renderer_never_states_a_case_the_validators_would_refuse() -> None:
    """The table is built from `ROLE_CASE`, and this is what keeps it built from
    it: a student must never be shown a case that would have failed validation."""
    for role, case in ROLE_CASE.items():
        assert inflection_for(role) == CASE_NAME[case]


def test_the_table_names_no_role_that_does_not_exist() -> None:
    assert set(ROLE_INFLECTION) <= ROLES


# --- which source wins --------------------------------------------------------------


def test_the_role_beats_the_morphology() -> None:
    """A مفعول به is منصوب because it is a مفعول به. A nominative reading of the
    ending is the analyzer being wrong, not a second opinion worth printing."""
    assert inflection_for("مفعول به", Case.NOM) == CASE_NAME[Case.ACC]


def test_a_role_with_no_case_of_its_own_takes_the_morphology() -> None:
    """صفة is the reason this fallback exists: an adjective's case is the case of
    the noun it follows, so the role genuinely cannot know it."""
    assert inflection_for("صفة", Case.GEN) == CASE_NAME[Case.GEN]
    assert inflection_for("صفة", Case.NOM) == CASE_NAME[Case.NOM]


def test_a_built_word_has_no_inflection_to_name() -> None:
    """A ماضٍ and a حرف are مبني; there is no case word for them."""
    assert inflection_for("فعل ماضٍ") is None
    assert inflection_for("حرف جزم") is None
    assert inflection_for("حرف نصب") is None


def test_an_unreadable_case_returns_silence_not_a_default() -> None:
    assert inflection_for("صفة", Case.UNKNOWN) is None
    assert inflection_for("صفة", Case.NULL) is None
    assert inflection_for("صفة", None) is None


def test_nothing_known_at_all_is_silence() -> None:
    assert inflection_for(None, None) is None


# --- verbs ------------------------------------------------------------------------


def test_the_mood_is_read_from_the_role_not_the_features() -> None:
    """يقرأُ / يقرأَ / يقرأْ are spelled identically, so morphology reports
    `unknown` on nearly every undiacritized مضارع. The rule that assigned the
    role recovered the mood from the governing particle, so it is the authority."""
    assert inflection_for("فعل مضارع مجزوم") == Inflection("مجزوم", "جزم")
    assert inflection_for("فعل مضارع منصوب", Case.NOM) == Inflection("منصوب", "نصب")


def test_a_covert_agent_still_has_a_case_to_sit_in() -> None:
    """It is مبني, so it will be phrased as في محل رفع -- but the رفع has to come
    from somewhere, and it comes from here."""
    assert inflection_for("فاعل — ضمير مستتر") == CASE_NAME[Case.NOM]


def test_inflections_are_frozen() -> None:
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        CASE_NAME[Case.NOM].adjective = "منصوب"  # type: ignore[misc]


def test_a_verb_whose_role_names_its_clause_falls_back_to_its_mood() -> None:
    """`خبر — جملة فعلية` describes the clause a verb heads and says nothing
    about the verb. يقرأ in الولد يقرأ is an ordinary مضارع مرفوع, and without
    this it would come out with no inflection at all."""
    assert inflection_for("خبر — جملة فعلية", None, Mood.INDICATIVE) == CASE_NAME[Case.NOM]


def test_the_role_still_beats_the_mood() -> None:
    """The rule recovered the mood from the عامل; morphology usually could not
    read it, and where they disagree the rule is the one that knew."""
    assert inflection_for("فعل مضارع مجزوم", None, Mood.INDICATIVE) == MOOD_NAME[Mood.JUSSIVE]


def test_an_unreadable_mood_is_silence_not_a_default() -> None:
    assert inflection_for("خبر — جملة فعلية", None, Mood.UNKNOWN) is None
    assert inflection_for("خبر — جملة فعلية", None, Mood.NULL) is None
