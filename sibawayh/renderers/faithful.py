"""Checking that a model's rewrite still says what it was given.

The model is asked to make an إعراب line friendlier, not to reconsider it. This
is the check that it did only that. It is small on purpose: three facts, and if
any of them failed to survive the rewrite, the reply is discarded.

* **the role** — مبتدأ has to still be مبتدأ
* **the case** — منصوب has to still be منصوب
* **the sign** — الياء has to still be الياء
* **the reason** — if the reply explains itself, the explanation has to be one
  the rule actually gave

Word order, register, phrasing, warmth — all of that is the point of asking a
model at all, and none of it is checked. What may not change is any fact the
layers below decided.

**The fourth is the one that took an argument to get right.** A reply can keep
the role, the case and the sign perfectly and still teach something false:
*نعت مرفوع وعلامة رفعه الضمة، لأنه جمع مذكر سالم* passes the first three and its
reason is nonsense. And the reason is the part that teaches — a student who
memorizes a wrong justification has learned something worse than nothing.

`Token.evidence` is what the rule actually observed, and `reasons.py` turns those
keys into Arabic. Each carries an anchor word, and a reply that explains itself
has to contain at least one of them. That is a test for *groundedness*, not for
correctness: it says the explanation came from the evidence rather than from the
model's memory. A reply that keeps the facts and offers no reason at all is
refused too, since the template line says exactly as much and is not a guess.

**Comparison ignores diacritics.** A model writing منصوبٌ has not disagreed with
منصوب, and rejecting it would discard a correct reply over a tanween. The words
are compared as bare letters, which is the same normalization the rest of the
project uses when it needs to match a word rather than read it.

**A fact of several words need not appear as one phrase.** Asked to explain إنّ,
the model wrote *حرف توكيد ونصب* — which is more complete than our own حرف نصب,
and which a contiguous match rejects. So each word of a fact is looked for in
turn, each after the last, and a word inside a longer one counts: ونصب contains
نصب, and refusing that would fail a reply for having a conjunction in it.

This is a check for drift, not a parser. It catches the reply that says مرفوع
where the analysis said منصوب, or الفتحة where it said الياء, which is what a
careless rewrite actually does. It is not proof that the sentence means what it
should, and nothing here pretends otherwise.

**A failure is never surfaced as a failure.** The caller falls back to the
template line, which is the correct answer in plainer words. The student sees a
less friendly sentence and never a wrong one.
"""

from __future__ import annotations

from dataclasses import dataclass

from sibawayh.diacritics import split_marks
from sibawayh.renderers.inflection import inflection_for
from sibawayh.renderers.phrases import phrase_for
from sibawayh.renderers.reasons import reasons_in
from sibawayh.renderers.signs import sign_for
from sibawayh.schema import Token


def bare(text: str) -> str:
    """`text` with every diacritic removed, for comparing words rather than
    reading them."""
    return "".join(base for base, _ in split_marks(text))


@dataclass(frozen=True)
class Facts:
    """What a rewrite of one token's line has to preserve."""

    role: str | None = None
    case: str | None = None
    mark: str | None = None

    @property
    def stated(self) -> tuple[str, ...]:
        return tuple(fact for fact in (self.role, self.case, self.mark) if fact)


def facts_of(token: Token) -> Facts:
    """The facts a model may not change, taken from the same tables the template
    renderer used to build the line it was given."""
    if token.irab_role is None:
        return Facts()

    phrase = phrase_for(token.irab_role)
    inflection = inflection_for(token.irab_role, token.feats.case, token.feats.mood)
    sign = sign_for(token, inflection) if inflection else None
    return Facts(
        role=phrase.head,
        case=inflection.adjective if inflection and not phrase.states_inflection else None,
        mark=sign.mark if sign else None,
    )


def appears_in(text: str, phrase: str) -> bool:
    """Whether every word of `phrase` occurs in `text`, each after the last.

    Both are compared bare. Words rather than the whole phrase, because a model
    elaborating inside a phrase — حرف **توكيد و**نصب — has not dropped it.
    """
    written, at = bare(text), 0
    for word in bare(phrase).split():
        found = written.find(word, at)
        if found < 0:
            return False
        at = found + len(word)
    return True


def missing_from(reply: str, facts: Facts) -> tuple[str, ...]:
    """Which of `facts` the reply failed to keep, in the order they were stated.

    Empty means the rewrite is faithful and may be shown.
    """
    return tuple(fact for fact in facts.stated if not appears_in(reply, fact))


def anchors_of(token: Token) -> tuple[str, ...]:
    """The words that would show an explanation came from this token's evidence."""
    return tuple(reason.anchor for reason in reasons_in(token.evidence))


def is_grounded(reply: str, token: Token) -> bool:
    """Whether the reply's explanation, if any, came from the rule's own evidence.

    True when the token records no reason at all: there is nothing to be grounded
    in, and demanding one would refuse every reply for a token the rules said
    little about.
    """
    anchors = anchors_of(token)
    if not anchors:
        return True
    return any(appears_in(reply, anchor) for anchor in anchors)


def is_faithful(reply: str, token: Token) -> bool:
    """Whether `reply` may be shown to a student in place of the template line."""
    return not missing_from(reply, facts_of(token)) and is_grounded(reply, token)
