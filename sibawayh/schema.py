"""Pydantic models for tokens, analyses and sentences.

Three models, as laid out in CLAUDE.md:

* `Features` / `Token` — one word (or inserted covert pronoun) with its morphology,
  its head, and the role the rule engine derived for it.
* `Analysis` — one *candidate reading* of a token. The CAMeL disambiguator returns a
  ranked list, and the runners-up live in `Token.alternatives`; the score margin
  between them is a confidence signal.
* `Sentence` — an ordered list of tokens plus the raw input.

Two conventions that the rest of the pipeline depends on:

`parser_label` and `irab_role` are separate fields and are never merged. The parser
supplies attachment, the rule engine supplies roles.

Feature values distinguish three kinds of absence, and the distinction is load-bearing:

===========  ==============================================================
`None`       not analyzed yet — the layer that fills this has not run
`"null"`     analyzed, not applicable (CAMeL `na`; a verb has no case)
`"unknown"`  analyzed, undetermined (CAMeL `u`) — **must trigger abstention**
===========  ==============================================================

Collapsing `"null"` and `"unknown"` would make undiacritized input look confident.
Note that `"null"` is the JSON *string* `"null"`, never JSON `null`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ROOT_HEAD = 0
"""Value of `Token.head` for the token that heads the sentence."""


class Aspect(StrEnum):
    PERFECT = "perfect"
    IMPERFECT = "imperfect"
    IMPERATIVE = "imperative"
    NULL = "null"


class Mood(StrEnum):
    INDICATIVE = "indicative"
    SUBJUNCTIVE = "subjunctive"
    JUSSIVE = "jussive"
    NULL = "null"
    UNKNOWN = "unknown"


class Case(StrEnum):
    NOM = "nom"
    ACC = "acc"
    GEN = "gen"
    NULL = "null"
    UNKNOWN = "unknown"


class State(StrEnum):
    CONSTRUCT = "construct"
    DEF = "def"
    INDEF = "indef"
    NULL = "null"
    UNKNOWN = "unknown"


class Voice(StrEnum):
    ACTIVE = "active"
    PASSIVE = "passive"
    NULL = "null"
    UNKNOWN = "unknown"


class Gender(StrEnum):
    M = "m"
    F = "f"
    BOTH = "b"
    """Valid as either gender — CAMeL `gen=b`, e.g. a participle unmarked for gender."""
    NULL = "null"
    UNKNOWN = "unknown"


class Number(StrEnum):
    S = "s"
    D = "d"
    P = "p"
    BOTH = "b"
    """Valid as either number — CAMeL `num=b`."""
    NULL = "null"
    UNKNOWN = "unknown"


class Person(StrEnum):
    FIRST = "1"
    SECOND = "2"
    THIRD = "3"
    NULL = "null"


class Pos(StrEnum):
    """Our coarse POS set. CAMeL's finer tag survives in `Token.pos_fine`."""

    NOUN = "noun"
    PROPN = "propn"
    ADJ = "adj"
    VERB = "verb"
    PRON = "pron"
    PREP = "prep"
    CONJ = "conj"
    PART = "part"
    ADV = "adv"
    PUNCT = "punct"


class Source(StrEnum):
    """Which layer produced a field, so we know which layer to fix."""

    CAMEL = "camel"
    PARSER = "parser"
    ARCS = "arcs"
    COVERT = "covert"
    RULES = "rules"
    LLM = "llm"
    GOLD = "gold"


class Features(BaseModel):
    """Morphological features in our vocabulary, never CAMeL's codes.

    `gen`/`num` are the *functional* values, not `form_gen`/`form_num`; agreement
    checks (صفة) depend on that distinction.

    Extra keys are allowed so hand-written gold data can carry occasional
    annotations we have not modeled (e.g. `defective`) without losing them on a
    round trip.
    """

    model_config = ConfigDict(extra="allow")

    aspect: Aspect | None = None
    mood: Mood | None = None
    case: Case | None = None
    state: State | None = None
    voice: Voice | None = None
    gen: Gender | None = None
    num: Number | None = None
    person: Person | None = None

    @field_validator("person", mode="before")
    @classmethod
    def _person_as_str(cls, value: Any) -> Any:
        """Accept `3` as well as `"3"`; CAMeL emits strings, humans write ints."""
        return str(value) if isinstance(value, int) else value


class Analysis(BaseModel):
    """One candidate reading of a token, as returned by the disambiguator.

    The top-ranked reading is promoted onto the `Token` itself; the rest stay in
    `Token.alternatives`. `score` is whatever the producing layer ranks by — only
    differences between analyses of the same token are meaningful.
    """

    model_config = ConfigDict(extra="forbid")

    diac: str | None = None
    lemma: str | None = None
    root: str | None = None
    pos: Pos | None = None
    pos_fine: str | None = None
    feats: Features = Field(default_factory=Features)
    score: float | None = None
    source: Source | None = None


class Token(BaseModel):
    """One word of the sentence, or a covert pronoun we inserted.

    `head` is the id of the governing token, or `ROOT_HEAD` (0) for the token that
    heads the sentence. Under i'rab that root is the first word of the sentence,
    which is not where UD or PADT put it — see `arcs.py`.
    """

    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=1)
    form: str = Field(min_length=1)
    diac: str | None = None
    lemma: str | None = None
    root: str | None = None
    pos: Pos | None = None
    pos_fine: str | None = None
    feats: Features = Field(default_factory=Features)

    head: int | None = Field(default=None, ge=ROOT_HEAD)
    parser_label: str | None = None
    arc_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    """How sure the parser was of *this attachment*. Raw evidence for the
    combined `confidence` below, never a substitute for it."""

    irab_role: str | None = None
    rule_id: str | None = None
    evidence: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    provenance: dict[str, Source] = Field(default_factory=dict)
    alternatives: list[Analysis] = Field(default_factory=list)
    inserted: bool = False

    @field_validator("provenance")
    @classmethod
    def _provenance_keys_are_fields(cls, value: dict[str, Source]) -> dict[str, Source]:
        unknown = sorted(set(value) - set(cls.model_fields))
        if unknown:
            raise ValueError(f"provenance keys must name Token fields; got {unknown}")
        return value

    @model_validator(mode="after")
    def _no_self_head(self) -> Token:
        if self.head is not None and self.head == self.id:
            raise ValueError(f"token {self.id} is its own head")
        return self


class Sentence(BaseModel):
    """A sentence and its tokens.

    The structural invariants enforced here are the ones that hold at *every* stage
    of the pipeline: ids are 1..n in order, and a head that is set points at a real
    token. Single-rootedness is deliberately not checked — tokens carry `head=None`
    until the parser runs. Tree-level validation belongs to the validator layer.
    """

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    sentence: str
    tokens: list[Token] = Field(default_factory=list)

    category: str | None = None
    tier: int | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _ids_are_sequential(self) -> Sentence:
        expected = list(range(1, len(self.tokens) + 1))
        actual = [token.id for token in self.tokens]
        if actual != expected:
            raise ValueError(f"token ids must be {expected}, got {actual}")
        return self

    @model_validator(mode="after")
    def _heads_resolve(self) -> Sentence:
        limit = len(self.tokens)
        dangling = [t.id for t in self.tokens if t.head is not None and t.head > limit]
        if dangling:
            raise ValueError(f"tokens {dangling} have heads outside 0..{limit}")
        return self

    def by_id(self, token_id: int) -> Token:
        """The token with this id. `token_id` is 1-based; 0 is ROOT, not a token."""
        return self.tokens[token_id - 1]

    def head_of(self, token: Token) -> Token | None:
        """The governing token, or `None` at the root or before parsing."""
        if token.head is None or token.head == ROOT_HEAD:
            return None
        return self.by_id(token.head)
