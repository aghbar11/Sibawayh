"""The template renderer: an إعراب line built from tables, with no model involved.

Everything the other modules in this package produce is a fragment. This is what
puts them in order, and the order is fixed because traditional i'rab is taught as
a formula — that is what makes a template possible at all.

A declinable word:

    مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة على آخره
    ↑     ↑     ↑                                    ↑
    head  case  sign                                 tail, if the role has one

A مبني word says two other things where the case would have been:

    حرف جر مبني على السكون لا محل له من الإعراب، والجار والمجرور في محل رفع خبر

And a covert pronoun, which was never written and so has no ending at all:

    ضمير مستتر تقديره هو في محل رفع فاعل

**Every clause can be dropped, and dropping is what makes this honest.** No role
means no line — the renderer declines and the caller shows morphology. A role but
no readable case stops after the role. A case whose sign belongs to a declension
class this project has not verified stops after the case. `الكِتابانِ: مبتدأ
مرفوع` is thin and true, and `وعلامة رفعه الضمة` would be false.

**Nothing here decides anything.** The role came from the rule engine, the case
from the role or from the analyzer, the sign from the word's own shape. This
module chooses word order and punctuation. That is the entire difference between
a renderer and the layers above it, and it is enforced by the return type: a
`Rendering` carries strings and cannot carry a role.
"""

from __future__ import annotations

from collections.abc import Sequence

from sibawayh.covert import INSERTED_MARK
from sibawayh.renderers.base import Renderer, Rendering
from sibawayh.renderers.built import NO_PLACE, built_on, is_built, place_of
from sibawayh.renderers.inflection import Inflection, inflection_for
from sibawayh.renderers.phrases import Phrase, phrase_for
from sibawayh.renderers.signs import sign_for
from sibawayh.schema import Aspect, Mood, Pos, Token, Voice

VERB_BY_ASPECT = {
    Aspect.PERFECT: "فعل ماضٍ",
    Aspect.IMPERFECT: "فعل مضارع",
    Aspect.IMPERATIVE: "فعل أمر",
}
"""How to name a verb the role does not name.

Needed for `خبر — جملة فعلية`, whose role describes the clause a verb heads and
says nothing about the verb itself.
"""

PASSIVE = "مبني للمجهول"
COVERT = "ضمير مستتر تقديره"
BUILT_ON = "مبني على"

MOOD_IMPLIES_IMPERFECT = frozenset({Mood.INDICATIVE, Mood.SUBJUNCTIVE, Mood.JUSSIVE})
"""Moods only a مضارع can carry, so a token reporting one is a مضارع."""

PLACELESS_POS = frozenset({Pos.PART, Pos.PREP, Pos.CONJ})
"""Which مبني words say لا محل له من الإعراب.

The حروف do. A ماضٍ is مبني too, but school i'rab stops at مبني على الفتح for it
rather than adding a clause about a slot a verb was never competing for.
"""


def _verb_named_by_its_morphology(token: Token) -> str | None:
    """What to call a verb when the role does not.

    A reported mood stands in for a missing aspect. Only a مضارع inflects for
    mood, so a token carrying one is a مضارع whether or not `aspect` says so —
    and the eval set has exactly that token: يقرأ in محمد يقرأ الكتاب is annotated
    with `mood` and no `aspect`.
    """
    named = VERB_BY_ASPECT.get(token.feats.aspect) if token.feats.aspect else None
    if named is None and token.feats.mood in MOOD_IMPLIES_IMPERFECT:
        named = VERB_BY_ASPECT[Aspect.IMPERFECT]
    if named is None:
        return None
    if token.feats.voice is Voice.PASSIVE:
        return f"{named} {PASSIVE}"
    return named


def _opening(token: Token, phrase: Phrase) -> str | None:
    """The phrase that names the word, or `None` if nothing can name it."""
    if phrase.head is not None:
        return phrase.head
    if token.pos is Pos.VERB:
        return _verb_named_by_its_morphology(token)
    return None


def _declined(token: Token, opening: str, phrase: Phrase, inflection: Inflection | None) -> str:
    """A معرب word: the case, then the sign that carries it, as far as each is known."""
    parts = [opening]
    if inflection is None:
        return " ".join(parts)

    if not phrase.states_inflection:
        parts.append(inflection.adjective)

    sign = sign_for(token, inflection)
    if sign is not None:
        parts.append(f"وعلامة {inflection.noun}ه {sign.text}")
    return " ".join(parts)


def _built(token: Token, opening: str, slot: Inflection | None) -> str:
    """A مبني word: what it is built on, and what slot it fills.

    `slot` is the case of the role alone — never one read off the word, and never
    a mood. A مبني word cannot show a case, so any case on it belongs to the slot
    it occupies rather than to the word, and only a role that names a slot can
    supply one. Live morphology reports a mood on perfect verbs, and taking it
    would produce *كُتِبَت: فعل ماضٍ مبني للمجهول مبني على الفتح في محل رفع فعل
    ماضٍ مبني للمجهول*, which is how this was found.
    """
    if token.inserted:
        # The marker says the token was never typed; it is bookkeeping, and
        # printing it would put an asterisk in the middle of an Arabic sentence.
        written = (token.diac or token.form).removesuffix(INSERTED_MARK)
        parts = [f"{COVERT} {written}"]
    else:
        on = built_on(token)
        parts = [opening] if on is None else [opening, f"{BUILT_ON} {on}"]

    place = place_of(slot, opening)
    if place != NO_PLACE:
        parts.append(place)
    elif token.pos in PLACELESS_POS:
        parts.append(NO_PLACE)
    return " ".join(parts)


def line_for(token: Token) -> str | None:
    """The إعراب of one token, or `None` where there is nothing to say.

    The word itself is not part of the line. The caller has the token and can put
    `diac` in front of it, which keeps this function returning only what it
    derived.
    """
    if token.irab_role is None:
        return None

    phrase = phrase_for(token.irab_role)
    opening = _opening(token, phrase)
    if opening is None:
        return None

    inflection = inflection_for(token.irab_role, token.feats.case, token.feats.mood)
    body = (
        _built(token, opening, inflection_for(token.irab_role))
        if is_built(token)
        else _declined(token, opening, phrase, inflection)
    )
    return f"{body}، {phrase.tail}" if phrase.tail else body


class TemplateRenderer(Renderer):
    """Builds every line from tables. No network, no key, no sampling.

    Exists so the model-backed renderer is optional rather than load-bearing:
    this one always answers, always the same way, and can be tested against fixed
    strings.
    """

    name = "template"
    deterministic = True

    def render(self, tokens: Sequence[Token]) -> Rendering:
        return Rendering.of([line_for(token) for token in tokens])
