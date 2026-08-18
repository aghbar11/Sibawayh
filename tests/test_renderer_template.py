"""The template renderer end to end, against every sentence of the eval set.

These are golden strings, checked by hand once and then held. They are the point
of a deterministic backend: the prose a student will read is now something with a
pass or a fail, not something to eyeball. A change to any table that alters a line
shows up here as a diff in Arabic, which is where it can be judged.

Driven off gold analyses rather than the live pipeline. What is under test is the
prose, and feeding it a wrong role would only test that a wrong role renders.
"""

from __future__ import annotations

import json
from pathlib import Path

from sibawayh.renderers import describe
from sibawayh.renderers.template import TemplateRenderer, line_for
from sibawayh.schema import (
    Aspect,
    Case,
    Features,
    Mood,
    Number,
    Person,
    Pos,
    Sentence,
    Token,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))
GOLD = {record["id"]: Sentence.model_validate(record) for record in EVAL["sentences"]}

EXPECTED: dict[str, list[str | None]] = {
    "verbal_overt_agent_01": [
        "فعل مضارع مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "فاعل مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "مفعول به منصوب وعلامة نصبه الفتحة الظاهرة على آخره",
    ],
    "verbal_perfect_01": [
        "فعل ماضٍ مبني على الفتح",
        "فاعل مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "مفعول به منصوب وعلامة نصبه الفتحة الظاهرة على آخره",
    ],
    "verbal_passive_01": [
        "فعل ماضٍ مبني للمجهول مبني على الفتح",
        "نائب فاعل مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
    ],
    "nominal_single_predicate_01": [
        "مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "خبر مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
    ],
    "nominal_pp_predicate_01": [
        "مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "حرف جر مبني على السكون لا محل له من الإعراب، والجار والمجرور في محل رفع خبر",
        "اسم مجرور وعلامة جره الكسرة الظاهرة على آخره",
    ],
    "nominal_adv_predicate_01": [
        "مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "ظرف مكان منصوب وعلامة نصبه الفتحة الظاهرة على آخره، والظرف في محل رفع خبر",
        "مضاف إليه مجرور وعلامة جره الكسرة الظاهرة على آخره",
    ],
    "nominal_verbal_predicate_01": [
        "مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "فعل مضارع مرفوع وعلامة رفعه الضمة الظاهرة على آخره، والجملة الفعلية في محل رفع خبر",
        "ضمير مستتر تقديره هو في محل رفع فاعل",
        "مفعول به منصوب وعلامة نصبه الفتحة الظاهرة على آخره",
    ],
    "nasikh_kana_01": [
        "فعل ماضٍ ناقص مبني على الفتح",
        "اسم كان مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "خبر كان منصوب وعلامة نصبه الفتحة الظاهرة على آخره",
    ],
    "nasikh_inna_01": [
        "حرف نصب مبني على الفتح لا محل له من الإعراب",
        "اسم إنّ منصوب وعلامة نصبه الياء لأنه جمع مذكر سالم",
        "خبر إنّ مرفوع وعلامة رفعه الواو لأنه جمع مذكر سالم",
    ],
    "jussive_lam_01": [
        "حرف جزم مبني على السكون لا محل له من الإعراب",
        "فعل مضارع مجزوم وعلامة جزمه السكون",
        "فاعل مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "مفعول به منصوب وعلامة نصبه الفتحة الظاهرة على آخره",
    ],
    "subjunctive_lan_01": [
        "حرف نصب مبني على السكون لا محل له من الإعراب",
        "فعل مضارع منصوب وعلامة نصبه الفتحة الظاهرة على آخره",
        "فاعل مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "مفعول به منصوب وعلامة نصبه الفتحة الظاهرة على آخره",
    ],
    "idafa_01": [
        "مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة على آخره، وهو مضاف",
        "مضاف إليه مجرور وعلامة جره الكسرة الظاهرة على آخره",
        "خبر مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
    ],
    "sifa_01": [
        "مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "نعت مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
        "خبر مرفوع وعلامة رفعه الضمة الظاهرة على آخره",
    ],
}


def rendered(sentence_id: str) -> list[str | None]:
    return list(describe(GOLD[sentence_id].tokens, TemplateRenderer()).lines)


# --- every sentence -----------------------------------------------------------------


def test_every_eval_sentence_renders_as_expected() -> None:
    for sentence_id in GOLD:
        assert rendered(sentence_id) == EXPECTED[sentence_id], sentence_id


def test_no_token_of_the_eval_set_goes_unsaid() -> None:
    """Abstention is a feature, but not here: every gold token has a role, and a
    None in this set would mean a table lost something it used to know."""
    missing = [
        (sentence_id, token.form)
        for sentence_id, sentence in GOLD.items()
        for token, line in zip(sentence.tokens, rendered(sentence_id), strict=True)
        if line is None
    ]
    assert not missing


def test_the_expectations_cover_the_whole_eval_set() -> None:
    assert set(EXPECTED) == set(GOLD)


# --- the shapes worth naming --------------------------------------------------------


def test_a_plain_declined_noun() -> None:
    assert rendered("nominal_single_predicate_01")[0] == (
        "مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة على آخره"
    )


def test_a_sound_masculine_plural_takes_a_letter_not_a_harakat() -> None:
    """The line a naive template gets wrong: العراقيين is accusative and signed
    by الياء."""
    assert rendered("nasikh_inna_01")[1] == "اسم إنّ منصوب وعلامة نصبه الياء لأنه جمع مذكر سالم"


def test_a_particle_is_built_and_fills_no_slot() -> None:
    assert rendered("nasikh_inna_01")[0] == "حرف نصب مبني على الفتح لا محل له من الإعراب"


def test_a_preposition_carries_a_clause_about_its_phrase() -> None:
    assert rendered("nominal_pp_predicate_01")[1] == (
        "حرف جر مبني على السكون لا محل له من الإعراب، والجار والمجرور في محل رفع خبر"
    )


def test_a_covert_pronoun_is_estimated_not_built() -> None:
    """It was never written, so there is no ending to be built on."""
    assert rendered("nominal_verbal_predicate_01")[2] == "ضمير مستتر تقديره هو في محل رفع فاعل"


def test_the_marker_never_reaches_the_student() -> None:
    """`هو*` is bookkeeping. An asterisk in the middle of an Arabic line is a bug."""
    assert "*" not in str(rendered("nominal_verbal_predicate_01")[2])


def test_a_verb_whose_role_names_its_clause_is_named_by_its_morphology() -> None:
    """The role خبر — جملة فعلية says nothing about the verb, and this token
    carries a mood but no aspect."""
    assert rendered("nominal_verbal_predicate_01")[1] == (
        "فعل مضارع مرفوع وعلامة رفعه الضمة الظاهرة على آخره، والجملة الفعلية في محل رفع خبر"
    )


def test_a_past_verb_stops_at_what_it_is_built_on() -> None:
    """School i'rab does not add a clause about a slot a verb was never
    competing for."""
    assert rendered("verbal_perfect_01")[0] == "فعل ماضٍ مبني على الفتح"


def test_the_passive_says_so() -> None:
    assert rendered("verbal_passive_01")[0] == "فعل ماضٍ مبني للمجهول مبني على الفتح"


def test_an_idafa_says_the_first_word_is_one() -> None:
    assert rendered("idafa_01")[0] == ("مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة على آخره، وهو مضاف")


def test_a_genitive_is_not_said_twice() -> None:
    """The role's phrase is اسم مجرور, which already states the case."""
    assert rendered("nominal_pp_predicate_01")[2] == (
        "اسم مجرور وعلامة جره الكسرة الظاهرة على آخره"
    )


def test_a_jussive_verb_is_signed_by_a_sukun() -> None:
    assert rendered("jussive_lam_01")[1] == "فعل مضارع مجزوم وعلامة جزمه السكون"


# --- what it declines to say --------------------------------------------------------


def test_no_role_means_no_line() -> None:
    """The rules abstained, so the caller shows morphology and the renderer says
    nothing rather than filling the shape."""
    assert line_for(Token(id=1, form="محمد", diac="مُحَمَّدٌ", pos=Pos.NOUN)) is None


def test_an_unreadable_case_stops_after_the_role() -> None:
    """صفة is the role that can reach this: its case is the noun's rather than
    the role's, so an unreadable ending leaves nothing to say. A مبتدأ cannot —
    the role fixes its case whatever the analyzer managed to read."""
    token = Token(
        id=1,
        form="جديد",
        diac="جَديد",
        pos=Pos.ADJ,
        irab_role="صفة",
        feats=Features(case=Case.UNKNOWN, num=Number.S),
    )
    assert line_for(token) == "نعت"


def test_an_unverified_declension_stops_after_the_case() -> None:
    """الكِتابانِ: مبتدأ مرفوع is thin and true. وعلامة رفعه الضمة would be false."""
    token = Token(
        id=1,
        form="الكتابان",
        diac="الكِتابانِ",
        lemma="كِتاب",
        pos=Pos.NOUN,
        irab_role="مبتدأ",
        feats=Features(case=Case.NOM, num=Number.D),
    )
    assert line_for(token) == "مبتدأ مرفوع"


def test_a_verb_with_neither_aspect_nor_mood_cannot_be_named() -> None:
    token = Token(id=1, form="كتب", pos=Pos.VERB, irab_role="خبر — جملة فعلية")
    assert line_for(token) is None


# --- the backend ---------------------------------------------------------------------


def test_the_backend_declares_itself_deterministic() -> None:
    """It is what lets these golden strings be asserted at all, and what lets a
    caller fall back to it when a model is unavailable."""
    assert TemplateRenderer().deterministic


def test_rendering_the_same_sentence_twice_gives_the_same_prose() -> None:
    assert rendered("sifa_01") == rendered("sifa_01")


def test_a_line_never_carries_the_word_itself() -> None:
    """The caller has the token and puts `diac` in front. Keeping the word out
    means this function returns only what it derived."""
    sentence = GOLD["sifa_01"]
    for token, line in zip(sentence.tokens, rendered("sifa_01"), strict=True):
        assert token.form not in str(line)


def test_an_imperative_is_named_too() -> None:
    """No eval sentence has one, so this is the only thing holding the entry."""
    token = Token(
        id=1,
        form="اكتب",
        diac="اُكْتُبْ",
        pos=Pos.VERB,
        irab_role="خبر — جملة فعلية",
        feats=Features(aspect=Aspect.IMPERATIVE),
    )
    assert str(line_for(token)).startswith("فعل أمر")


def test_a_built_word_takes_its_place_from_the_role_alone() -> None:
    """Live morphology reports a mood on perfect verbs. Taking it produced
    `فعل ماضٍ مبني للمجهول مبني على الفتح في محل رفع فعل ماضٍ مبني للمجهول`,
    which is how this was found. A مبني word cannot show a case, so any case on
    it belongs to a slot, and only a role that names a slot may supply one."""
    token = Token(
        id=1,
        form="كتبت",
        diac="كُتِبَت",
        pos=Pos.VERB,
        irab_role="فعل ماضٍ مبني للمجهول",
        feats=Features(aspect=Aspect.PERFECT, mood=Mood.INDICATIVE, person=Person.THIRD),
    )
    assert line_for(token) == "فعل ماضٍ مبني للمجهول مبني على الفتح"
