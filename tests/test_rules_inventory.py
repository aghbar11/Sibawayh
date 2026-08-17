"""The rest of the rule inventory: nawasikh, nominal, idafa, modifiers, particles.

The headline test is `test_every_eval_token_is_correctly_labelled` — the plan's
own target for this step. Everything else exists to pin the *discriminators*,
because most of these roles are separated by one morphological feature and
nothing structural at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sibawayh.rules import apply_rules, default_registry
from sibawayh.rules.idafa import IDAFA_ANNEXED
from sibawayh.rules.modifiers import ADJECTIVE, PREP_OBJECT
from sibawayh.rules.nawasikh import (
    INNA_PREDICATE,
    KANA_SUBJECT,
)
from sibawayh.rules.nominal import PREDICATE_SINGLE, TOPIC
from sibawayh.schema import Features, Pos, Sentence, Token

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))[
    "sentences"
]
EVAL_IDS = [s["id"] for s in EVAL]


def analysed(sentence_id: str) -> tuple[list[Token], list[Token]]:
    raw = next(s for s in EVAL if s["id"] == sentence_id)
    gold = Sentence.model_validate(raw).tokens
    blank = [t.model_copy(update={"irab_role": None, "rule_id": None}) for t in gold]
    return gold, apply_rules(blank)


def role_of(sentence_id: str, form: str) -> tuple[str | None, str | None]:
    _, result = analysed(sentence_id)
    token = next(t for t in result if t.form == form)
    return token.irab_role, token.rule_id


# --- the target -------------------------------------------------------------------


@pytest.mark.parametrize("raw", EVAL, ids=EVAL_IDS)
def test_every_eval_token_is_correctly_labelled(raw: dict) -> None:
    """The plan's target for this step: every eval sentence fully labelled."""
    gold = Sentence.model_validate(raw).tokens
    result = apply_rules([t.model_copy(update={"irab_role": None}) for t in gold])
    assert [t.irab_role for t in result] == [t.irab_role for t in gold]
    assert all(token.rule_id is not None for token in result)


def test_the_whole_eval_set_at_once() -> None:
    """A single number, so a regression shows up as a number going down."""
    correct = sum(
        produced.irab_role == expected.irab_role
        for raw in EVAL
        for produced, expected in zip(
            apply_rules(
                [
                    t.model_copy(update={"irab_role": None})
                    for t in Sentence.model_validate(raw).tokens
                ]
            ),
            Sentence.model_validate(raw).tokens,
            strict=True,
        )
    )
    assert correct == 40


def test_every_rule_has_a_unique_id_and_a_description() -> None:
    registry = default_registry()
    ids = [rule.id for rule in registry]
    assert len(ids) == len(set(ids))
    assert all(rule.description for rule in registry)
    assert all(rule.role for rule in registry)


# --- النواسخ: the head's lemma is the discriminator ---------------------------------


def test_kana_assigns_nominative_to_its_subject() -> None:
    assert role_of("nasikh_kana_01", "اليوم") == ("اسم كان", "KANA_SUBJECT")
    assert role_of("nasikh_kana_01", "رائعا") == ("خبر كان", "KANA_PREDICATE")


def test_inna_inverts_the_pattern() -> None:
    """The point of `nasikh_inna_01`: accusative is the اسم, nominative the خبر."""
    assert role_of("nasikh_inna_01", "العراقيين") == ("اسم إنّ", "INNA_SUBJECT")
    assert role_of("nasikh_inna_01", "قادرون") == ("خبر إنّ", "INNA_PREDICATE")


def test_the_same_case_means_opposite_roles_under_the_two_families() -> None:
    """A nominative is اسم كان under كان and خبر إنّ under إنّ. Only the head's
    lemma separates them — no feature of the token itself can."""
    nominative = Token(id=2, form="س", pos=Pos.NOUN, head=1, feats=Features(case="nom"))
    kana = Token(id=1, form="كان", pos=Pos.VERB, head=0, feats=Features(aspect="perfect"))
    inna = Token(id=1, form="إن", pos=Pos.PART, head=0)

    assert KANA_SUBJECT(nominative, kana, [kana, nominative]) is not None
    assert INNA_PREDICATE(nominative, kana, [kana, nominative]) is None
    assert INNA_PREDICATE(nominative, inna, [inna, nominative]) is not None
    assert KANA_SUBJECT(nominative, inna, [inna, nominative]) is None


def test_kana_verb_is_named_defective() -> None:
    assert role_of("nasikh_kana_01", "كان") == ("فعل ماضٍ ناقص", "KANA_VERB")


def test_nawasikh_evidence_names_the_family() -> None:
    _, result = analysed("nasikh_inna_01")
    subject = next(t for t in result if t.form == "العراقيين")
    assert "head_lemma_in_inna_sisters" in subject.evidence
    assert "case=acc" in subject.evidence


# --- الجملة الاسمية ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sentence_id", "form"),
    [
        ("nominal_single_predicate_01", "الشمس"),
        ("nominal_pp_predicate_01", "العصفور"),
        ("nominal_adv_predicate_01", "الكتاب"),
        ("nominal_verbal_predicate_01", "محمد"),
        ("sifa_01", "الكتاب"),
    ],
)
def test_the_root_nominal_is_the_topic(sentence_id: str, form: str) -> None:
    assert role_of(sentence_id, form) == ("مبتدأ", "TOPIC")


def test_a_construct_topic_says_so() -> None:
    """كتاب الطالب جديد: gold names it مبتدأ — مضاف, not plain مبتدأ."""
    assert role_of("idafa_01", "كتاب") == ("مبتدأ — مضاف", "TOPIC_ANNEXING")


@pytest.mark.parametrize(
    ("sentence_id", "form", "role", "rule_id"),
    [
        ("nominal_single_predicate_01", "مشرقة", "خبر", "PREDICATE_SINGLE"),
        ("idafa_01", "جديد", "خبر", "PREDICATE_SINGLE"),
        ("sifa_01", "مفيد", "خبر", "PREDICATE_SINGLE"),
        ("nominal_verbal_predicate_01", "يقرأ", "خبر — جملة فعلية", "PREDICATE_VERBAL"),
        ("nominal_pp_predicate_01", "في", "حرف جر — خبر شبه جملة", "PREDICATE_PREPOSITIONAL"),
        ("nominal_adv_predicate_01", "فوق", "ظرف مكان — خبر شبه جملة", "PREDICATE_ADVERBIAL"),
    ],
)
def test_all_three_predicate_shapes(sentence_id: str, form: str, role: str, rule_id: str) -> None:
    assert role_of(sentence_id, form) == (role, rule_id)


def test_an_inserted_pronoun_is_never_the_topic() -> None:
    """A covert agent sits under a verb, but nothing may promote it to مبتدأ."""
    pronoun = Token(
        id=1, form="هو*", pos=Pos.PRON, head=0, inserted=True, feats=Features(case="nom")
    )
    assert TOPIC(pronoun, None, [pronoun]) is None


# --- صفة vs خبر: definiteness, and nothing else -------------------------------------


def test_definiteness_separates_sifa_from_khabar() -> None:
    """الكتاب الجديد مفيد — CLAUDE.md calls this the confusion the engine will
    make. Both adjectives are nominative and hang off the same noun."""
    assert role_of("sifa_01", "الجديد") == ("صفة", "ADJECTIVE")
    assert role_of("sifa_01", "مفيد") == ("خبر", "PREDICATE_SINGLE")


def test_flipping_definiteness_flips_the_role() -> None:
    """The same tree, one feature changed, the opposite answer."""
    noun = Token(id=1, form="الكتاب", pos=Pos.NOUN, head=0, feats=Features(case="nom", state="def"))
    sentence = [noun]

    agreeing = Token(
        id=2, form="الجديد", pos=Pos.ADJ, head=1, feats=Features(case="nom", state="def")
    )
    disagreeing = agreeing.model_copy(update={"feats": Features(case="nom", state="indef")})

    assert ADJECTIVE(agreeing, noun, sentence) is not None
    assert PREDICATE_SINGLE(agreeing, noun, sentence) is None
    assert ADJECTIVE(disagreeing, noun, sentence) is None
    assert PREDICATE_SINGLE(disagreeing, noun, sentence) is not None


def test_an_unknown_state_abstains_on_both() -> None:
    """Definiteness is the only discriminator, so without it there is no answer."""
    noun = Token(id=1, form="الكتاب", pos=Pos.NOUN, head=0, feats=Features(case="nom", state="def"))
    unclear = Token(id=2, form="جديد", pos=Pos.ADJ, head=1, feats=Features(case="nom"))
    assert ADJECTIVE(unclear, noun, [noun, unclear]) is None
    assert PREDICATE_SINGLE(unclear, noun, [noun, unclear]) is None


def test_a_disagreeing_case_is_not_a_sifa() -> None:
    noun = Token(id=1, form="الكتاب", pos=Pos.NOUN, head=0, feats=Features(case="nom", state="def"))
    accusative = Token(
        id=2, form="الجديد", pos=Pos.ADJ, head=1, feats=Features(case="acc", state="def")
    )
    assert ADJECTIVE(accusative, noun, [noun, accusative]) is None


def test_sifa_evidence_records_the_agreement() -> None:
    _, result = analysed("sifa_01")
    adjective = next(t for t in result if t.form == "الجديد")
    assert "definiteness_agrees" in adjective.evidence


# --- الإضافة -------------------------------------------------------------------------


def test_genitive_under_a_construct_noun_is_annexed() -> None:
    assert role_of("idafa_01", "الطالب") == ("مضاف إليه", "IDAFA_ANNEXED")
    assert role_of("nominal_adv_predicate_01", "الطاولة") == ("مضاف إليه", "IDAFA_ANNEXED")


def test_construct_state_is_required() -> None:
    """CLAUDE.md: `idafa_01` is the test that `stt=c` is wired through. Without
    the construct state there is no إضافة, whatever the case says."""
    plain = Token(id=1, form="كتاب", pos=Pos.NOUN, head=0, feats=Features(case="nom", state="def"))
    genitive = Token(id=2, form="الطالب", pos=Pos.NOUN, head=1, feats=Features(case="gen"))
    assert IDAFA_ANNEXED(genitive, plain, [plain, genitive]) is None

    construct = plain.model_copy(update={"feats": Features(case="nom", state="construct")})
    assert IDAFA_ANNEXED(genitive, construct, [construct, genitive]) is not None


def test_genitive_case_is_required() -> None:
    construct = Token(
        id=1, form="كتاب", pos=Pos.NOUN, head=0, feats=Features(case="nom", state="construct")
    )
    nominative = Token(id=2, form="الطالب", pos=Pos.NOUN, head=1, feats=Features(case="nom"))
    assert IDAFA_ANNEXED(nominative, construct, [construct, nominative]) is None


# --- الحروف ---------------------------------------------------------------------------


def test_particles_are_named_for_what_they_govern() -> None:
    assert role_of("jussive_lam_01", "لم") == ("حرف جزم", "JUSSIVE_PARTICLE")
    assert role_of("subjunctive_lan_01", "لن") == ("حرف نصب", "SUBJUNCTIVE_PARTICLE")
    assert role_of("nasikh_inna_01", "إن") == ("حرف نصب", "INNA_PARTICLE")


def test_lam_and_inna_share_a_role_string_but_not_a_rule() -> None:
    """Same answer, different reasons — so the hint text can differ."""
    _, lam = analysed("subjunctive_lan_01")
    _, inna = analysed("nasikh_inna_01")
    particle = next(t for t in lam if t.form == "لن")
    nasikh = next(t for t in inna if t.form == "إن")
    assert particle.irab_role == nasikh.irab_role == "حرف نصب"
    assert particle.rule_id != nasikh.rule_id
    assert "governs_mood=subjunctive" in particle.evidence
    assert "governs_case=acc" in nasikh.evidence


def test_a_jussive_particle_needs_a_jussive_verb_under_it() -> None:
    """لا is both a jussive particle and an ordinary negator; the verb's mood is
    what says which one this is."""
    lam = Token(id=1, form="لا", pos=Pos.PART, head=0)
    indicative = Token(id=2, form="يقرأ", pos=Pos.VERB, head=1, feats=Features(mood="indicative"))
    result = apply_rules([lam, indicative])
    assert result[0].irab_role is None


# --- ordering -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("specific", "general"),
    [
        ("COVERT_AGENT", "VERBAL_AGENT"),
        ("PASSIVE_AGENT", "VERBAL_AGENT"),
        ("TOPIC_ANNEXING", "TOPIC"),
        ("KANA_SUBJECT", "VERBAL_AGENT"),
        ("KANA_PREDICATE", "VERBAL_OBJECT"),
        ("ADJECTIVE", "PREDICATE_SINGLE"),
    ],
)
def test_specific_rules_outrank_general_ones(specific: str, general: str) -> None:
    """First-match-wins makes this ordering load-bearing, not cosmetic."""
    ordered = [rule.id for rule in default_registry()]
    assert ordered.index(specific) < ordered.index(general)


@pytest.mark.parametrize("raw", EVAL, ids=EVAL_IDS)
def test_no_two_rules_at_the_same_priority_both_match(raw: dict) -> None:
    """The invariant the perfect-verb bug broke.

    `Registry` sorts on `(priority, id)`, so when two rules share a priority the
    winner is decided **alphabetically**. That is deterministic but arbitrary:
    `VERB_IMPERFECT_INDICATIVE` beat `VERB_PERFECT_ACTIVE` on `I` before `P`,
    and named a past-tense verb مضارع. Renaming either rule would have changed
    the answer.

    Overlap is fine where a real priority gap decides it — `COVERT_AGENT` (10)
    is meant to outrank `VERBAL_AGENT` (110). What must never happen is two
    rules tying and the spelling breaking the tie.
    """
    registry = list(default_registry())
    tokens = Sentence.model_validate(raw).tokens
    for token in tokens:
        head = next((t for t in tokens if t.id == token.head), None)
        matched = [rule for rule in registry if rule(token, head, tokens) is not None]
        priorities = [rule.priority for rule in matched]
        assert len(priorities) == len(set(priorities)), (
            f"{token.form}: {[(r.id, r.priority) for r in matched]} — "
            "tied priority, so the alphabet picks the answer"
        )


def test_no_tie_on_morphology_as_camel_actually_returns_it() -> None:
    """The gold-driven test above cannot catch the bug that motivated it.

    Gold sets `aspect` **or** `mood` on a verb, never both, so a rule keyed on
    mood alone simply does not fire on gold data. CAMeL sets both — كتب comes
    back `aspect=perfect` *and* `mood=indicative` — and that is what created the
    tie. So the tie check has to run on a token shaped the way the analyser
    really shapes it, not the way the eval set is written.
    """
    verb = Token(
        id=1,
        form="كتب",
        pos=Pos.VERB,
        head=0,
        feats=Features(aspect="perfect", mood="indicative", voice="active"),
    )
    matched = [rule for rule in default_registry() if rule(verb, None, [verb]) is not None]
    priorities = [rule.priority for rule in matched]
    assert len(priorities) == len(set(priorities)), [(r.id, r.priority) for r in matched]
    assert apply_rules([verb])[0].irab_role == "فعل ماضٍ"


def test_the_only_overlap_is_the_intended_one() -> None:
    """Records which tokens more than one rule claims, so a new overlap shows up
    as a test failure rather than as a silently different answer."""
    registry = list(default_registry())
    overlapping = []
    for raw in EVAL:
        tokens = Sentence.model_validate(raw).tokens
        for token in tokens:
            head = next((t for t in tokens if t.id == token.head), None)
            matched = [rule.id for rule in registry if rule(token, head, tokens) is not None]
            if len(matched) > 1:
                overlapping.append((raw["id"], token.form, sorted(matched)))
    assert overlapping == [
        (
            "nominal_verbal_predicate_01",
            "هو*",
            ["COVERT_AGENT", "VERBAL_AGENT"],
        )
    ]


def test_prep_object_outranks_everything_that_could_shadow_it() -> None:
    ordered = [rule.id for rule in default_registry()]
    assert ordered.index("PREP_OBJECT") < ordered.index("IDAFA_ANNEXED")
    assert PREP_OBJECT.role == "مجرور"
