"""Morphology tests, driven by recorded CAMeL output — never a live model call.

`tests/data/camel_analyses.json` holds real `MLEDisambiguator` output for the eval
sentences plus three clitic cases. Regenerate it by hand when the CAMeL version
changes; the suite must stay offline and fast.

The one test that does load a model is marked `camel` and skipped unless the data
is installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sibawayh.morphology import (
    ABSENT,
    CAMEL_ASPECT,
    CAMEL_CASE,
    CAMEL_GENDER,
    CAMEL_MOOD,
    CAMEL_NUMBER,
    CAMEL_PERSON,
    CAMEL_POS,
    CAMEL_STATE,
    CAMEL_VOICE,
    CLITIC_POS,
    NO_ANALYSIS,
    MorphologyError,
    _split_d3tok,
    sentence_from_analyses,
    tokens_from_word,
    translate_analysis,
    translate_features,
    translate_pos,
)
from sibawayh.schema import Case, Gender, Number, Pos, Sentence, Source, State, Voice

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (REPO_ROOT / "tests" / "data" / "camel_analyses.json").read_text(encoding="utf-8")
)
RECORDED = FIXTURE["sentences"]


def words_of(sentence_id: str) -> list[tuple[str, list[tuple[dict[str, Any], float]]]]:
    """The recorded (word, ranked analyses) pairs, in the shape the pure API wants."""
    return [
        (word["word"], [(a["analysis"], a["score"]) for a in word["analyses"]])
        for word in RECORDED[sentence_id]["words"]
    ]


def build(sentence_id: str) -> Sentence:
    record = RECORDED[sentence_id]
    return sentence_from_analyses(record["text"], words_of(sentence_id), sentence_id=sentence_id)


EVAL_IDS = [sid for sid in RECORDED if not sid.startswith(("clitic", "attached", "interrog"))]


# --- the code tables must cover everything the database can emit ------------------

# Recorded from MorphologyDB.builtin_db().defines for morphology-db-msa-r13. Hard-coded
# so this test does not need the database installed; update alongside the tables.
DB_DEFINES = {
    "asp": ["c", "i", "na", "p"],
    "mod": ["i", "j", "na", "s", "u"],
    "cas": ["a", "g", "n", "na", "u"],
    "stt": ["c", "d", "i", "na", "u"],
    "vox": ["a", "na", "p", "u"],
    "gen": ["b", "f", "m", "na", "u"],
    "num": ["b", "d", "na", "p", "s", "u"],
    "per": ["1", "2", "3", "na"],
    "pos": [
        "abbrev",
        "adj",
        "adj_comp",
        "adj_num",
        "adv",
        "adv_interrog",
        "adv_rel",
        "conj",
        "conj_sub",
        "digit",
        "interj",
        "latin",
        "noun",
        "noun_num",
        "noun_prop",
        "noun_quant",
        "part",
        "part_det",
        "part_focus",
        "part_fut",
        "part_interrog",
        "part_neg",
        "part_restrict",
        "part_verb",
        "part_voc",
        "prep",
        "pron",
        "pron_dem",
        "pron_exclam",
        "pron_interrog",
        "pron_rel",
        "punc",
        "verb",
        "verb_pseudo",
    ],
    "prc0": ["Al_det", "lA_neg", "mA_neg", "mA_part", "mA_rel"],
    "prc1": [
        "bi_part",
        "bi_prep",
        "fiy_prep",
        "hA_dem",
        "ka_prep",
        "la_emph",
        "la_prep",
        "la_rc",
        "li_jus",
        "li_prep",
        "li_sub",
        "sa_fut",
        "ta_prep",
        "wA_voc",
        "wa_prep",
        "yA_voc",
    ],
    "prc2": ["fa_conj", "fa_conn", "fa_rc", "fa_sub", "wa_conj", "wa_part", "wa_sub"],
    "prc3": [">a_ques"],
    "enc0_other": [
        "Ah_voc",
        "lA_neg",
        "mA_interrog",
        "mA_rel",
        "mA_sub",
        "ma_interrog",
        "ma_rel",
        "ma_sub",
        "man_interrog",
        "man_rel",
    ],
}

TABLES = {
    "asp": CAMEL_ASPECT,
    "mod": CAMEL_MOOD,
    "cas": CAMEL_CASE,
    "stt": CAMEL_STATE,
    "vox": CAMEL_VOICE,
    "gen": CAMEL_GENDER,
    "num": CAMEL_NUMBER,
    "per": CAMEL_PERSON,
    "pos": CAMEL_POS,
}


@pytest.mark.parametrize("field", sorted(TABLES))
def test_feature_table_covers_database(field: str) -> None:
    missing = sorted(set(DB_DEFINES[field]) - set(TABLES[field]))
    assert not missing, f"{field}: unmapped CAMeL values {missing}"


@pytest.mark.parametrize("field", ["prc0", "prc1", "prc2", "prc3", "enc0_other"])
def test_clitic_table_covers_database(field: str) -> None:
    """Every clitic code becomes a token, except ال, which is a feature."""
    expected = set(DB_DEFINES[field]) - {"Al_det"}
    missing = sorted(expected - set(CLITIC_POS))
    assert not missing, f"{field}: unmapped clitic codes {missing}"


@pytest.mark.parametrize("field", sorted(TABLES))
def test_absent_value_is_mapped(field: str) -> None:
    """Backoff analyses put `-` in most fields; nothing may crash on it."""
    assert ABSENT in TABLES[field] or field == "pos"


# --- translation -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("noun", Pos.NOUN),
        ("noun_num", Pos.NOUN),
        ("noun_prop", Pos.PROPN),
        ("adj_comp", Pos.ADJ),
        ("verb_pseudo", Pos.VERB),
        ("pron_rel", Pos.PRON),
        ("part_neg", Pos.PART),
        ("abbrev", Pos.NOUN),
        ("digit", Pos.NOUN),
        ("interj", Pos.PART),
        ("punc", Pos.PUNCT),
    ],
)
def test_translate_pos(code: str, expected: Pos) -> None:
    assert translate_pos(code) == expected


def test_translate_pos_rejects_unknown_code() -> None:
    with pytest.raises(MorphologyError, match="unmapped CAMeL pos"):
        translate_pos("noun_of_the_future")


def test_na_and_u_stay_distinct() -> None:
    """CLAUDE.md trap 2: `na` is not-applicable, `u` is undetermined. Only `u`
    is a confidence problem, so collapsing them would hide abstention triggers."""
    not_applicable = translate_features({"cas": "na", "stt": "na"})
    undetermined = translate_features({"cas": "u", "stt": "u"})
    assert not_applicable.case == Case.NULL
    assert undetermined.case == Case.UNKNOWN
    assert not_applicable.case != undetermined.case


def test_absent_maps_to_unknown_not_null() -> None:
    feats = translate_features({"gen": ABSENT, "num": ABSENT, "cas": ABSENT})
    assert feats.gen == Gender.UNKNOWN
    assert feats.num == Number.UNKNOWN
    assert feats.case == Case.UNKNOWN


def test_both_gender_and_number() -> None:
    feats = translate_features({"gen": "b", "num": "b"})
    assert feats.gen == Gender.BOTH
    assert feats.num == Number.BOTH


def test_missing_field_stays_none() -> None:
    """Absent key means the layer has not run — distinct from `null`/`unknown`."""
    assert translate_features({"cas": "n"}).voice is None


def test_translate_features_rejects_unknown_value() -> None:
    with pytest.raises(MorphologyError, match="unmapped CAMeL cas"):
        translate_features({"cas": "z"})


def test_translate_analysis_records_provenance_and_score() -> None:
    analysis = {"diac": "كِتابٍ", "lex": "كِتاب", "root": "ك.ت.ب", "pos": "noun", "cas": "g"}
    result = translate_analysis(analysis, score=0.94)
    assert result.lemma == "كِتاب"
    assert result.pos == Pos.NOUN
    assert result.pos_fine == "noun"
    assert result.score == 0.94
    assert result.source == Source.CAMEL


# --- d3tok segmentation ----------------------------------------------------------


@pytest.mark.parametrize(
    ("d3tok", "expected"),
    [
        ("كِتابِ", ([], "كِتابِ", [])),
        ("ال+_كِتابِ", (["ال"], "كِتابِ", [])),
        ("كِتابِ_+هُ", ([], "كِتابِ", ["هُ"])),
        ("بِ+_ال+_كِتابِ", (["بِ", "ال"], "كِتابِ", [])),
        ("أَ+_تَ+_قْرَأ_+هُ", (["أَ", "تَ"], "قْرَأ", ["هُ"])),
        ("", ([], "", [])),
    ],
)
def test_split_d3tok(d3tok: str, expected: tuple[list[str], str, list[str]]) -> None:
    assert _split_d3tok(d3tok) == expected


# --- token building --------------------------------------------------------------


def test_al_is_a_feature_not_a_token() -> None:
    """CLAUDE.md is explicit: ال التعريف is `state=def`, never its own token.
    d3tok splits it anyway, so the surface has to be folded back onto the stem."""
    sentence = build("sifa_01")
    assert len(sentence.tokens) == 3
    assert sentence.tokens[0].form.startswith("ال")
    assert sentence.tokens[0].feats.state == State.DEF


def test_idafa_carries_construct_state() -> None:
    """`stt=c` is the إضافة signal; idafa_01 is the test that it reaches us."""
    sentence = build("idafa_01")
    assert sentence.tokens[0].feats.state == State.CONSTRUCT
    assert sentence.tokens[0].feats.case == Case.GEN


def test_attached_preposition_becomes_its_own_token() -> None:
    sentence = build("attached_preposition")
    forms = [token.form for token in sentence.tokens]
    assert len(forms) == 5, forms  # four words, بـ split off
    preposition = sentence.tokens[1]
    assert preposition.pos == Pos.PREP
    assert sentence.tokens[2].form.startswith("ال")


def test_joined_pronoun_carries_its_role_and_features() -> None:
    """`enc0=3ms_poss` hands us مضاف إليه directly — person, gender, number and
    genitive case all follow from the code."""
    sentence = build("clitic_pronoun")
    assert len(sentence.tokens) == 3
    pronoun = sentence.tokens[-1]
    assert pronoun.pos == Pos.PRON
    assert pronoun.feats.person == "3"
    assert pronoun.feats.gen == Gender.M
    assert pronoun.feats.num == Number.S
    assert pronoun.feats.case == Case.GEN
    assert pronoun.feats.model_extra == {"clitic_role": "poss"}
    assert sentence.tokens[1].feats.state == State.CONSTRUCT


def test_backoff_analysis_falls_back_to_the_surface_word() -> None:
    """An out-of-vocabulary word comes back as NOAN with `-` features. The token
    must keep the word the student typed, not the NOAN sentinel."""
    record = RECORDED["interrogative_hamza"]
    top = record["words"][0]["analyses"][0]["analysis"]
    assert top["d3tok"] == NO_ANALYSIS

    sentence = build("interrogative_hamza")
    unanalyzed = sentence.tokens[0]
    assert unanalyzed.form == record["words"][0]["word"]
    assert unanalyzed.feats.case == Case.UNKNOWN
    assert unanalyzed.feats.gen == Gender.UNKNOWN


def test_word_with_no_analyses_raises() -> None:
    with pytest.raises(MorphologyError, match="no analyses"):
        tokens_from_word("كتاب", [])


# --- sentence assembly, over every recorded sentence ------------------------------


@pytest.mark.parametrize("sentence_id", sorted(RECORDED), ids=sorted(RECORDED))
def test_sentence_builds_and_validates(sentence_id: str) -> None:
    sentence = build(sentence_id)
    assert sentence.tokens
    assert [t.id for t in sentence.tokens] == list(range(1, len(sentence.tokens) + 1))


@pytest.mark.parametrize("sentence_id", sorted(RECORDED), ids=sorted(RECORDED))
def test_morphology_leaves_syntax_alone(sentence_id: str) -> None:
    """This layer supplies morphology only. Attachment is the parser's, roles are
    the rule engine's, and neither may be filled in here."""
    for token in build(sentence_id).tokens:
        assert token.head is None
        assert token.parser_label is None
        assert token.irab_role is None
        assert token.rule_id is None
        assert token.confidence is None


@pytest.mark.parametrize("sentence_id", sorted(RECORDED), ids=sorted(RECORDED))
def test_token_count_never_below_word_count(sentence_id: str) -> None:
    """Clitics may add tokens; nothing may lose one."""
    assert len(build(sentence_id).tokens) >= len(RECORDED[sentence_id]["words"])


@pytest.mark.parametrize("sentence_id", EVAL_IDS, ids=EVAL_IDS)
def test_eval_sentences_are_one_token_per_word(sentence_id: str) -> None:
    """The tier-1 eval set has no clitics, so the token count must match the word
    count exactly. A change here means segmentation started splitting ال again."""
    sentence = build(sentence_id)
    assert len(sentence.tokens) == len(sentence.sentence.split())


@pytest.mark.parametrize("sentence_id", sorted(RECORDED), ids=sorted(RECORDED))
def test_stem_tokens_are_attributed_to_camel(sentence_id: str) -> None:
    """Every token says CAMeL gave it its POS; stems say so about features too.
    Clitic tokens are typed from a feature code, so they carry no feature block."""
    for token in build(sentence_id).tokens:
        assert token.provenance["pos"] == Source.CAMEL
        assert token.provenance.get("feats") in (Source.CAMEL, None)


@pytest.mark.parametrize("sentence_id", sorted(RECORDED), ids=sorted(RECORDED))
def test_alternatives_exclude_the_promoted_reading(sentence_id: str) -> None:
    """The top reading lives on the token; `alternatives` holds only runners-up,
    and their scores are what the abstention layer reads as a margin."""
    for word, analyses in words_of(sentence_id):
        tokens = tokens_from_word(word, analyses)
        stem = next(t for t in tokens if "feats" in t.provenance)
        assert len(stem.alternatives) == len(analyses) - 1
        assert all(a.score is not None for a in stem.alternatives)
        assert all(t.alternatives == [] for t in tokens if t is not stem)


def test_alternatives_expose_a_thin_win() -> None:
    """كتبت is ambiguous undiacritized: active كَتَبَت wins, passive كُتِبَت is close
    behind. The passive reading has to survive into `alternatives`, or نائب فاعل
    can never be recovered."""
    verb = build("verbal_passive_01").tokens[0]
    assert verb.feats.voice == Voice.ACTIVE
    passives = [a for a in verb.alternatives if a.feats.voice == Voice.PASSIVE]
    assert passives, "passive reading was dropped"
    assert passives[0].score is not None and passives[0].score > 0.9


def test_top_analysis_can_be_wrong() -> None:
    """إن comes back as `pos=abbrev` ahead of the إِنَّ reading. Recorded as a fact
    about the analyzer, not a wish: the rule layer must not trust rank 1 blindly."""
    inna = build("nasikh_inna_01").tokens[0]
    assert inna.pos_fine == "abbrev"
    assert any(a.pos_fine == "verb_pseudo" for a in inna.alternatives)


# --- the live path, off by default ------------------------------------------------


@pytest.mark.camel
def test_live_analyze_matches_the_fixture() -> None:
    """Guards the fixture against silent CAMeL drift. Run with `-m camel`."""
    pytest.importorskip("camel_tools")
    from sibawayh.morphology import CamelMorphology

    analyzer = CamelMorphology(top=FIXTURE["top"])
    for sentence_id in EVAL_IDS:
        expected = build(sentence_id)
        actual = analyzer.analyze(RECORDED[sentence_id]["text"], sentence_id=sentence_id)
        assert [t.form for t in actual.tokens] == [t.form for t in expected.tokens]
        assert [t.pos for t in actual.tokens] == [t.pos for t in expected.tokens]
