"""Tests for the role-to-words table.

The table is hand-written, so the test that matters most is the one holding it
to the inventory the validators publish. A role the rules can emit and this table
has never heard of would reach a student as a crash or as an unreviewed term.
"""

from __future__ import annotations

import pytest
from sibawayh.renderers.base import RenderError
from sibawayh.renderers.phrases import ROLE_PHRASE, phrase_for
from sibawayh.validate import ROLES


def test_every_role_the_validators_allow_has_words() -> None:
    assert not ROLES - set(ROLE_PHRASE)


def test_the_table_invents_no_roles() -> None:
    """Held in both directions, so the two grow together instead of drifting."""
    assert not set(ROLE_PHRASE) - ROLES


def test_a_plain_role_is_its_own_phrase() -> None:
    assert phrase_for("مبتدأ") == phrase_for("مبتدأ")
    assert phrase_for("مبتدأ").head == "مبتدأ"
    assert phrase_for("مبتدأ").tail == ""


def test_an_unknown_role_raises() -> None:
    """Echoing it back would put an unreviewed grammatical term in front of a
    student, which is worse than failing loudly."""
    with pytest.raises(RenderError, match="no phrasing for role"):
        phrase_for("تمييز")


# --- the five compound roles --------------------------------------------------------


def test_idafa_keeps_the_role_and_adds_a_note() -> None:
    phrase = phrase_for("مبتدأ — مضاف")
    assert phrase.head == "مبتدأ"
    assert phrase.tail == "وهو مضاف"


def test_a_preposition_is_named_by_the_first_half_and_the_phrase_by_the_second() -> None:
    phrase = phrase_for("حرف جر — خبر شبه جملة")
    assert phrase.head == "حرف جر"
    assert "خبر" in phrase.tail


def test_an_adverb_of_place_says_the_same_of_itself() -> None:
    phrase = phrase_for("ظرف مكان — خبر شبه جملة")
    assert phrase.head == "ظرف مكان"
    assert "الظرف" in phrase.tail


def test_a_verbal_predicate_names_the_clause_not_the_word() -> None:
    """The token is a verb; the role describes the clause it heads. Nothing here
    can name the word, so morphology has to."""
    phrase = phrase_for("خبر — جملة فعلية")
    assert phrase.head is None
    assert phrase.tail == "والجملة الفعلية في محل رفع خبر"


def test_a_covert_agent_is_phrased_like_any_other_agent() -> None:
    """The second half describes the token, not the role. What makes the line
    different lives on the token as `inserted`, not here."""
    assert phrase_for("فاعل — ضمير مستتر").head == phrase_for("فاعل").head


def test_the_em_dash_is_not_split_on() -> None:
    """Two compound roles put the role first and two put it second. A split
    would give the covert pronoun ضمير مستتر where فاعل belongs."""
    assert phrase_for("فاعل — ضمير مستتر").head != "ضمير مستتر"
    assert phrase_for("حرف جر — خبر شبه جملة").head != "خبر شبه جملة"


# --- inflection ---------------------------------------------------------------------


def test_the_imperfect_verb_states_its_own_mood() -> None:
    """`فعل مضارع مرفوع` is one phrase. Appending a case clause would say مرفوع
    twice, and the role is the better authority anyway: mood is unreadable on
    undiacritized input, and the rule recovered it from the governing particle."""
    for role in ("فعل مضارع مرفوع", "فعل مضارع منصوب", "فعل مضارع مجزوم"):
        assert phrase_for(role).states_inflection


def test_a_noun_role_states_no_inflection() -> None:
    for role in ("مبتدأ", "مفعول به", "اسم إنّ", "مضاف إليه"):
        assert not phrase_for(role).states_inflection


def test_the_past_verb_is_built_and_states_no_inflection() -> None:
    """A ماضٍ is مبني, so there is no mood word in its phrase to collide with."""
    assert not phrase_for("فعل ماضٍ").states_inflection
    assert phrase_for("فعل ماضٍ مبني للمجهول").head == "فعل ماضٍ مبني للمجهول"


def test_a_genitive_is_named_as_a_noun_not_as_a_property() -> None:
    """The role names a property; a line has to name a thing."""
    assert phrase_for("مجرور").head == "اسم مجرور"


def test_phrases_are_frozen() -> None:
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        phrase_for("مبتدأ").head = "خبر"  # type: ignore[misc]
