"""CAMeL Tools wrapper — the only module that knows CAMeL's vocabulary.

Everything CAMeL emits is terse codes: `asp=p`, `cas=u`, `stt=c`, `enc0=3ms_poss`.
Those codes are translated into our vocabulary *here*, and nothing downstream may
read them. If a rule needs to know something CAMeL encodes, add it to `Features`
and translate it in this module.

The layer splits cleanly in two, and the split is what makes it testable:

*Pure translation* — `translate_pos`, `translate_features`, `translate_analysis`,
`tokens_from_word`, `sentence_from_analyses`. These take plain dictionaries in the
shape CAMeL returns and produce our models. Tests drive them from recorded output
under `tests/data/`, so the suite never loads a model.

*The live call* — `CamelMorphology`, which loads the MSA disambiguator and hands
its output to the pure half. It imports `camel_tools` lazily so that importing
this module (and running most of the suite) works without the data installed.

Three things worth knowing about what CAMeL actually returns:

`Al_det` is a **feature, not a token.** The `d3tok` scheme emits `ال+` as its own
segment; we drop that segment and keep it as `state=def`. Every other clitic —
attached prepositions, the interrogative hamza, joined pronouns — does become a
token, because i'rab gives each of them a role.

`enc0` names the joined pronoun's role outright: `3ms_dobj` is مفعول به,
`3fs_poss` is مضاف إليه. That is handed to us for free, so it is recorded on the
clitic token as `feats.clitic_role`. It is a *hint from morphology*, not an
i'rab role — `irab_role` stays empty until the rule engine runs.

The top analysis is often wrong on short undiacritized input. إن comes back as
`pos=abbrev` ahead of the إِنَّ reading; كتبت prefers active كَتَبَت over passive
كُتِبَت. Runners-up are kept in `Token.alternatives` with their scores precisely
so the abstention layer can see how thin the win was.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from typing import Any

from sibawayh.diacritics import rank as rank_by_diacritics
from sibawayh.normalize import normalize, strip_diacritics
from sibawayh.schema import (
    Analysis,
    Aspect,
    Case,
    Features,
    Gender,
    Mood,
    Number,
    Person,
    Pos,
    Sentence,
    Source,
    State,
    Token,
    Voice,
)

DEFAULT_TOP = 5
"""How many analyses to ask the disambiguator for. One is promoted, the rest
become `alternatives`; the score gap between the first two is the margin the
abstention layer reads."""

NO_CLITIC = frozenset({"0", "na"})
"""`prc*`/`enc0` values meaning "no clitic here". `na` is not-applicable and `0`
is applicable-but-absent; neither produces a token."""

NO_ANALYSIS = "NOAN"
"""`d3tok` value on a backoff analysis — the word is out of vocabulary and CAMeL
guessed. Such an analysis carries `-` in most feature fields and must not be
segmented; the surface word is all we really have."""

ABSENT = "-"
"""Feature value on a backoff analysis: the analyzer produced nothing here. It is
a confidence problem, so it maps to `unknown` wherever the enum has one."""


# --- feature code tables ---------------------------------------------------------

CAMEL_ASPECT: dict[str, Aspect] = {
    "p": Aspect.PERFECT,
    "i": Aspect.IMPERFECT,
    "c": Aspect.IMPERATIVE,
    "na": Aspect.NULL,
    ABSENT: Aspect.NULL,  # no UNKNOWN member; only reachable on backoff non-verbs
}

CAMEL_MOOD: dict[str, Mood] = {
    "i": Mood.INDICATIVE,
    "s": Mood.SUBJUNCTIVE,
    "j": Mood.JUSSIVE,
    "na": Mood.NULL,
    "u": Mood.UNKNOWN,
    ABSENT: Mood.UNKNOWN,
}

CAMEL_CASE: dict[str, Case] = {
    "n": Case.NOM,
    "a": Case.ACC,
    "g": Case.GEN,
    "na": Case.NULL,
    "u": Case.UNKNOWN,
    ABSENT: Case.UNKNOWN,
}

CAMEL_STATE: dict[str, State] = {
    "c": State.CONSTRUCT,
    "d": State.DEF,
    "i": State.INDEF,
    "na": State.NULL,
    "u": State.UNKNOWN,
    ABSENT: State.UNKNOWN,
}

CAMEL_VOICE: dict[str, Voice] = {
    "a": Voice.ACTIVE,
    "p": Voice.PASSIVE,
    "na": Voice.NULL,
    "u": Voice.UNKNOWN,
    ABSENT: Voice.UNKNOWN,
}

CAMEL_GENDER: dict[str, Gender] = {
    "m": Gender.M,
    "f": Gender.F,
    "b": Gender.BOTH,
    "na": Gender.NULL,
    "u": Gender.UNKNOWN,
    ABSENT: Gender.UNKNOWN,
}

CAMEL_NUMBER: dict[str, Number] = {
    "s": Number.S,
    "d": Number.D,
    "p": Number.P,
    "b": Number.BOTH,
    "na": Number.NULL,
    "u": Number.UNKNOWN,
    ABSENT: Number.UNKNOWN,
}

CAMEL_PERSON: dict[str, Person] = {
    "1": Person.FIRST,
    "2": Person.SECOND,
    "3": Person.THIRD,
    "na": Person.NULL,
    ABSENT: Person.NULL,  # no UNKNOWN member
}

CAMEL_POS: dict[str, Pos] = {
    # nominals
    "noun": Pos.NOUN,
    "noun_num": Pos.NOUN,
    "noun_quant": Pos.NOUN,
    "noun_prop": Pos.PROPN,
    # abbreviations, numerals and foreign words fill nominal slots; CAMeL's own
    # CATiB tag for them is NOM. The exact tag survives in `pos_fine`.
    "abbrev": Pos.NOUN,
    "digit": Pos.NOUN,
    "foreign": Pos.NOUN,
    "latin": Pos.NOUN,
    # adjectives
    "adj": Pos.ADJ,
    "adj_comp": Pos.ADJ,
    "adj_num": Pos.ADJ,
    # verbs
    "verb": Pos.VERB,
    "verb_pseudo": Pos.VERB,
    # pronouns — the subtype is load-bearing (اسم إشارة vs اسم موصول)
    "pron": Pos.PRON,
    "pron_dem": Pos.PRON,
    "pron_rel": Pos.PRON,
    "pron_interrog": Pos.PRON,
    "pron_exclam": Pos.PRON,
    # particles — the subtype identifies لم / لن / لا
    "part": Pos.PART,
    "part_det": Pos.PART,
    "part_focus": Pos.PART,
    "part_fut": Pos.PART,
    "part_interrog": Pos.PART,
    "part_neg": Pos.PART,
    "part_restrict": Pos.PART,
    "part_verb": Pos.PART,
    "part_voc": Pos.PART,
    "interj": Pos.PART,
    # the rest
    "prep": Pos.PREP,
    "conj": Pos.CONJ,
    "conj_sub": Pos.CONJ,
    "adv": Pos.ADV,
    "adv_rel": Pos.ADV,
    "adv_interrog": Pos.ADV,
    "punc": Pos.PUNCT,
}


# --- clitic tables ---------------------------------------------------------------

AL_DET = "Al_det"
"""ال التعريف. A feature (`state=def`), never a token of its own."""

_ENCLITIC_PRONOUN = re.compile(
    r"^(?P<person>[123])(?P<gen>[mf])?(?P<num>[sdp])_(?P<role>dobj|poss|pron)$"
)

CLITIC_ROLES = frozenset({"dobj", "poss", "pron"})
"""The `enc0` suffixes. `dobj` is مفعول به, `poss` is مضاف إليه, `pron` is the
bare pronoun a particle or preposition governs."""

CLITIC_POS: dict[str, tuple[Pos, str]] = {
    # prc0 — everything except Al_det, which is handled as a feature
    "lA_neg": (Pos.PART, "part_neg"),
    "mA_neg": (Pos.PART, "part_neg"),
    "mA_part": (Pos.PART, "part"),
    "mA_rel": (Pos.PRON, "pron_rel"),
    # prc1 — attached prepositions, and the لام that governs mood
    "bi_prep": (Pos.PREP, "prep"),
    "bi_part": (Pos.PART, "part"),
    "ka_prep": (Pos.PREP, "prep"),
    "ta_prep": (Pos.PREP, "prep"),
    "wa_prep": (Pos.PREP, "prep"),
    "la_prep": (Pos.PREP, "prep"),
    "li_prep": (Pos.PREP, "prep"),
    "fiy_prep": (Pos.PREP, "prep"),
    "li_jus": (Pos.PART, "part_verb"),
    "li_sub": (Pos.PART, "part_verb"),
    "la_emph": (Pos.PART, "part_focus"),
    "la_rc": (Pos.PART, "part"),
    "sa_fut": (Pos.PART, "part_fut"),
    "hA_dem": (Pos.PRON, "pron_dem"),
    "wA_voc": (Pos.PART, "part_voc"),
    "yA_voc": (Pos.PART, "part_voc"),
    # prc2 — coordination. Tokenized now, attachment deferred (see CLAUDE.md).
    "wa_conj": (Pos.CONJ, "conj"),
    "fa_conj": (Pos.CONJ, "conj"),
    "wa_sub": (Pos.CONJ, "conj_sub"),
    "fa_sub": (Pos.CONJ, "conj_sub"),
    "wa_part": (Pos.PART, "part"),
    "fa_conn": (Pos.PART, "part"),
    "fa_rc": (Pos.PART, "part"),
    # prc3 — the interrogative hamza
    ">a_ques": (Pos.PART, "part_interrog"),
    # enc0 — the non-pronominal enclitics
    "mA_interrog": (Pos.PRON, "pron_interrog"),
    "mA_sub": (Pos.CONJ, "conj_sub"),
    "ma_interrog": (Pos.PRON, "pron_interrog"),
    "ma_rel": (Pos.PRON, "pron_rel"),
    "ma_sub": (Pos.CONJ, "conj_sub"),
    "man_interrog": (Pos.PRON, "pron_interrog"),
    "man_rel": (Pos.PRON, "pron_rel"),
    "Ah_voc": (Pos.PART, "part_voc"),
}

PROCLITIC_FIELDS = ("prc3", "prc2", "prc1", "prc0")
"""Proclitic feature fields in the order `d3tok` writes them, outermost first."""


class MorphologyError(ValueError):
    """CAMeL returned something this module has no mapping for."""


def _lookup(table: Mapping[str, Any], code: Any, field: str) -> Any:
    """Translate one code, or say loudly which one is unmapped."""
    try:
        return table[code]
    except KeyError:
        raise MorphologyError(f"unmapped CAMeL {field} value {code!r}") from None


def translate_pos(code: str) -> Pos:
    """Collapse a CAMeL POS tag onto our coarse set. `pos_fine` keeps the original."""
    return _lookup(CAMEL_POS, code, "pos")


def translate_features(analysis: Mapping[str, Any]) -> Features:
    """Morphological features, in our vocabulary.

    `gen`/`num` are the functional values, never `form_gen`/`form_num` — صفة
    agreement depends on the functional pair. Absent keys stay `None`, which
    means "not analyzed", and is distinct from `"null"` and `"unknown"`.
    """
    fields: list[tuple[str, str, Mapping[str, Any]]] = [
        ("aspect", "asp", CAMEL_ASPECT),
        ("mood", "mod", CAMEL_MOOD),
        ("case", "cas", CAMEL_CASE),
        ("state", "stt", CAMEL_STATE),
        ("voice", "vox", CAMEL_VOICE),
        ("gen", "gen", CAMEL_GENDER),
        ("num", "num", CAMEL_NUMBER),
        ("person", "per", CAMEL_PERSON),
    ]
    values = {
        ours: _lookup(table, analysis[theirs], theirs)
        for ours, theirs, table in fields
        if analysis.get(theirs) is not None
    }
    return Features(**values)


def translate_analysis(analysis: Mapping[str, Any], score: float | None = None) -> Analysis:
    """One CAMeL analysis dictionary as one candidate reading."""
    return Analysis(
        diac=analysis.get("diac"),
        lemma=analysis.get("lex"),
        root=analysis.get("root"),
        pos=translate_pos(analysis["pos"]),
        pos_fine=analysis["pos"],
        feats=translate_features(analysis),
        score=score,
        source=Source.CAMEL,
    )


# --- segmentation ----------------------------------------------------------------


def _split_d3tok(d3tok: str) -> tuple[list[str], str, list[str]]:
    """Split a `d3tok` string into (proclitics, stem, enclitics).

    CAMeL joins segments with `_` and marks direction with `+`: `ال+_كِتابِ` is a
    proclitic then a stem, `كِتابِ_+هُ` is a stem then an enclitic. A segment that
    is neither is part of the stem.
    """
    segments = [segment for segment in d3tok.split("_") if segment]
    proclitics = []
    enclitics = []
    index = 0
    while index < len(segments) and segments[index].endswith("+"):
        proclitics.append(segments[index].removesuffix("+"))
        index += 1
    end = len(segments)
    while end > index and segments[end - 1].startswith("+"):
        enclitics.insert(0, segments[end - 1].removeprefix("+"))
        end -= 1
    stem = "".join(segments[index:end])
    return proclitics, stem, enclitics


def _proclitic_codes(analysis: Mapping[str, Any]) -> list[str]:
    """Present proclitic codes, outermost first, matching `d3tok` segment order."""
    return [
        code
        for field in PROCLITIC_FIELDS
        if (code := analysis.get(field)) is not None and code not in NO_CLITIC
    ]


def _enclitic_codes(analysis: Mapping[str, Any]) -> list[str]:
    code = analysis.get("enc0")
    return [] if code is None or code in NO_CLITIC else [code]


def _clitic_token(token_id: int, diac: str, code: str) -> Token:
    """A token for one clitic, typed from its feature code.

    `diac` is the segment as CAMeL wrote it, diacritics and all; `form` is that
    segment bare, because `form` is what the student typed.

    A joined pronoun carries the person/gender/number its `enc0` code spells out,
    and the case that follows from its role: مضاف إليه is genitive, مفعول به is
    accusative. `_pron` — the pronoun after a particle or preposition — is left
    `unknown`, because which case it takes depends on the governor, and that is
    the rule engine's call.
    """
    form = strip_diacritics(diac)
    match = _ENCLITIC_PRONOUN.match(code)
    if match is not None:
        role = match.group("role")
        feats = Features(
            person=CAMEL_PERSON[match.group("person")],
            gen=CAMEL_GENDER[match.group("gen")] if match.group("gen") else Gender.BOTH,
            num=CAMEL_NUMBER[match.group("num")],
            case={"poss": Case.GEN, "dobj": Case.ACC}.get(role, Case.UNKNOWN),
            state=State.NULL,
            clitic_role=role,
        )
        return Token(
            id=token_id,
            form=form,
            diac=diac,
            pos=Pos.PRON,
            pos_fine="pron",
            feats=feats,
            provenance={"diac": Source.CAMEL, "pos": Source.CAMEL, "feats": Source.CAMEL},
        )

    pos, pos_fine = _lookup(CLITIC_POS, code, "clitic")
    return Token(
        id=token_id,
        form=form,
        diac=diac,
        lemma=diac,
        pos=pos,
        pos_fine=pos_fine,
        provenance={"diac": Source.CAMEL, "pos": Source.CAMEL},
    )


Clitic = tuple[str, str]
"""One clitic as (surface form, CAMeL feature code)."""


def _segment(word: str, top: Mapping[str, Any]) -> tuple[list[Clitic], str, list[Clitic]]:
    """Work out the token split for one word: (proclitics, stem, enclitics).

    Each clitic comes back as a (surface, feature code) pair. `ال` is not among
    them — its surface is folded back onto the stem, because `Al_det` is a
    feature and the student sees الكتاب as one word.

    The stem comes back diacritized, or as `""` when CAMeL produced no reading at
    all — a backoff analysis has no diacritization to offer, and inventing one
    would be a claim we cannot support. The caller falls back to the surface word.

    Segmentation is skipped, whole word kept, in two cases: a backoff analysis, and
    `d3tok` disagreeing with the `prc*`/`enc0` fields about how many clitics there
    are. Guessing an alignment there would attach the wrong role to the wrong piece.
    """
    d3tok = top.get("d3tok") or ""
    if not d3tok or d3tok == NO_ANALYSIS:
        return [], "", []

    proclitic_forms, stem, enclitic_forms = _split_d3tok(d3tok)
    proclitic_codes = _proclitic_codes(top)
    enclitic_codes = _enclitic_codes(top)
    if len(proclitic_forms) != len(proclitic_codes) or len(enclitic_forms) != len(enclitic_codes):
        return [], top.get("diac") or word, []

    proclitics = []
    for form, code in zip(proclitic_forms, proclitic_codes, strict=True):
        if code == AL_DET:
            stem = form + stem
        else:
            proclitics.append((form, code))
    enclitics = list(zip(enclitic_forms, enclitic_codes, strict=True))
    return proclitics, stem, enclitics


def _surface(
    word: str,
    typed: str | None,
    stem_diac: str,
    proclitics: Sequence[Clitic],
    enclitics: Sequence[Clitic],
) -> str:
    """What to show as the stem's `form`.

    The student's own spelling wherever it is the whole word, since that is what
    `form` promises and what they will look for on the page. Where clitics were
    split off, the stem is a part of the word rather than the word, and only the
    analysis knows where that part starts.
    """
    if proclitics or enclitics:
        return strip_diacritics(stem_diac) or word
    return strip_diacritics(typed) if typed else word


def tokens_from_word(
    word: str,
    analyses: Sequence[tuple[Mapping[str, Any], float | None]],
    start_id: int = 1,
    typed: str | None = None,
) -> list[Token]:
    """Turn one disambiguated word into one or more tokens.

    `analyses` is the ranked list for that word as (analysis, score) pairs; the
    first is promoted onto the stem token and the rest become its `alternatives`.
    Clitics are split off as their own tokens, `ال` excepted.

    `typed` is the word as the student actually spelled it, diacritics and all.
    When it carries marks, the analyses are reordered so the readings compatible
    with them come first — see `diacritics.py`. This has to happen before
    anything else here, because segmentation reads the top analysis.

    Ids run from `start_id` in surface order: proclitics, stem, enclitics.
    `head` is left `None` — attachment is the parser's job.
    """
    if not analyses:
        raise MorphologyError(f"word {word!r} has no analyses")

    ranking = rank_by_diacritics(typed or "", [str(a.get("diac") or "") for a, _ in analyses])
    analyses = [analyses[index] for index in ranking.order]

    top, _ = analyses[0]
    proclitics, stem_diac, enclitics = _segment(word, top)

    tokens = [
        _clitic_token(start_id + offset, diac, code)
        for offset, (diac, code) in enumerate(proclitics)
    ]

    stem = Token(
        id=start_id + len(tokens),
        # `form` is the word as typed, `diac` is CAMeL's diacritization of it. On a
        # backoff analysis there is no diacritization, and `diac` stays empty rather
        # than echoing the surface back as though it had been vowelled.
        #
        # Taken from the input and not from the analysis. CAMeL's chosen reading of
        # إن is أَنَّ, and deriving the form from it showed the student a different
        # word than the one they typed — on a page, their own sentence rewritten in
        # front of them. `diac` still carries the reading, which is where a claim
        # about vowelling belongs.
        #
        # Only where the word was not segmented. A clitic split makes the stem a
        # *part* of the word, and the analysis is then the only thing that knows
        # where the part begins.
        form=_surface(word, typed, stem_diac, proclitics, enclitics),
        diac=stem_diac or None,
        lemma=top.get("lex"),
        root=top.get("root"),
        pos=translate_pos(top["pos"]),
        pos_fine=top["pos"],
        feats=translate_features(top),
        provenance={
            "diac": Source.CAMEL,
            "lemma": Source.CAMEL,
            "root": Source.CAMEL,
            "pos": Source.CAMEL,
            "pos_fine": Source.CAMEL,
            "feats": Source.CAMEL,
        },
        # The top reading is promoted onto the token itself; only the runners-up
        # live here. CAMeL scores them relative to the winner, so the first
        # alternative's score *is* the margin the abstention layer needs.
        alternatives=[translate_analysis(analysis, score) for analysis, score in analyses[1:]],
        # Recorded only when the typed vowelling actually ruled something out.
        # `provenance` still says the features are CAMeL's, which is true — we
        # chose among CAMeL's own readings rather than inventing one.
        evidence=["typed_diacritics_chose_this_reading"] if ranking.decided else [],
    )
    tokens.append(stem)

    tokens.extend(
        _clitic_token(stem.id + 1 + offset, diac, code)
        for offset, (diac, code) in enumerate(enclitics)
    )
    return tokens


def sentence_from_analyses(
    text: str,
    words: Sequence[tuple[str, Sequence[tuple[Mapping[str, Any], float | None]]]],
    sentence_id: str | None = None,
    typed: Sequence[str] | None = None,
) -> Sentence:
    """Assemble a `Sentence` from (surface word, ranked analyses) pairs.

    `typed`, if given, is the same words as the student spelled them, one for
    one and in the same order — the diacritics normalization stripped before the
    analyzer ever saw them.

    Pure: this is the seam the tests drive with recorded CAMeL output.
    """
    if typed is not None and len(typed) != len(words):
        raise MorphologyError(f"{len(typed)} typed words for {len(words)} analyzed ones")

    tokens: list[Token] = []
    for index, (word, analyses) in enumerate(words):
        tokens.extend(
            tokens_from_word(
                word,
                analyses,
                start_id=len(tokens) + 1,
                typed=None if typed is None else typed[index],
            )
        )
    return Sentence(id=sentence_id, sentence=text, tokens=tokens)


# --- the live call ---------------------------------------------------------------


BERT = "bert"
"""Context-aware. Reads the whole sentence before choosing a reading."""

MLE = "mle"
"""Maximum-likelihood. Chooses each word's commonest reading in isolation."""

DEFAULT_DISAMBIGUATOR = BERT

DISAMBIGUATOR_ENV = "SIBAWAYH_DISAMBIGUATOR"
"""Set to `mle` to fall back — useful when the 445MB BERT data is absent."""


class DisambiguatorError(MorphologyError):
    """The requested disambiguator could not be loaded."""


class CamelMorphology:
    """The MSA disambiguator, wrapped.

    Two are available, and the choice matters more than anything else in this
    module. `mle` picks each word's commonest reading **in isolation**, so on a
    short undiacritized sentence it reads الرجل in يأكل الرجل السمك as accusative
    and the rule engine then calls the فاعل a مفعول به. `bert` reads the whole
    sentence and gets it right. Every case error measured against the eval set
    was an MLE error, and none survived the switch.

    The cost is size and speed: 445MB of model data, and inference rather than a
    table lookup. `mle` stays reachable through `$SIBAWAYH_DISAMBIGUATOR` for
    environments where that is too much, on the understanding that its case
    output cannot be trusted on short input.

    Loading is deferred to the first `analyze` call: importing this module must
    not require the CAMeL data to be installed.
    """

    def __init__(self, top: int = DEFAULT_TOP, kind: str | None = None) -> None:
        self.top = top
        self.kind = (kind or os.environ.get(DISAMBIGUATOR_ENV) or DEFAULT_DISAMBIGUATOR).lower()
        if self.kind not in {BERT, MLE}:
            raise DisambiguatorError(
                f"unknown disambiguator {self.kind!r}; expected {BERT} or {MLE}"
            )
        self._disambiguator: Any = None

    @property
    def disambiguator(self) -> Any:
        if self._disambiguator is None:
            self._disambiguator = self._load()
        return self._disambiguator

    def _load(self) -> Any:
        if self.kind == MLE:
            from camel_tools.disambig.mle import MLEDisambiguator

            return MLEDisambiguator.pretrained(top=self.top)

        from camel_tools.disambig.bert import BERTUnfactoredDisambiguator

        try:
            return BERTUnfactoredDisambiguator.pretrained(top=self.top)
        except Exception as error:  # pragma: no cover - depends on local data
            raise DisambiguatorError(
                "could not load the BERT disambiguator. Install it with "
                "`camel_data -i disambig-bert-unfactored-msa`, or set "
                f"${DISAMBIGUATOR_ENV}=mle to fall back — but note that MLE's case "
                "output is unreliable on short undiacritized input."
            ) from error

    def analyze(
        self,
        text: str,
        *,
        normalize_input: bool = True,
        sentence_id: str | None = None,
    ) -> Sentence:
        """Raw text in, a `Sentence` of morphologically analyzed tokens out.

        `Sentence.sentence` holds the normalized text, since that is what the
        token forms correspond to. Heads and i'rab roles are untouched.

        The words are tokenized twice: once as typed and once after
        normalization. The analyzer only ever sees the second — it dediacritizes
        its input anyway — while the first is kept so `tokens_from_word` can use
        the student's own vowelling to choose among the readings that come back.
        If the two tokenizations disagree on how many words there are, they
        cannot be lined up, and the typed forms are dropped rather than guessed
        at.
        """
        from camel_tools.tokenizers.word import simple_word_tokenize

        typed = simple_word_tokenize(text)
        if normalize_input:
            text = normalize(text)
        words = simple_word_tokenize(text)
        ranked = [
            (word.word, [(scored.analysis, scored.score) for scored in word.analyses])
            for word in self.disambiguator.disambiguate(words)
        ]
        return sentence_from_analyses(
            text,
            ranked,
            sentence_id=sentence_id,
            typed=typed if len(typed) == len(ranked) else None,
        )


def analyze(text: str, top: int = DEFAULT_TOP, kind: str | None = None, **kwargs: Any) -> Sentence:
    """Convenience wrapper. Loads a fresh model each call — fine for a one-shot
    CLI, wasteful in a loop; hold a `CamelMorphology` instead."""
    return CamelMorphology(top=top, kind=kind).analyze(text, **kwargs)
