"""What the model is shown, and nothing else.

A model asked to explain Arabic grammar from memory will produce fluent Arabic
grammar that is not about this sentence. So it is never asked to. It is handed
the finished analysis — the role the rules derived, the case, the sign, the
observations the rule fired on — and asked to say that back in friendlier words.

Everything in the payload was computed by a layer that can be checked. The
model's job begins after the last decision has already been made, which is what
CLAUDE.md means by *the LLM renders; it does not decide*.

**The template line is in the payload on purpose.** It is the correct answer,
already assembled, and including it turns the task from *analyze this word* into
*rewrite this sentence for a student*. The second task is one a model is reliably
good at; the first is the one it invents answers to.

**The reasons travel in Arabic.** `evidence` is a list of internal keys, and a
model handed `head_lemma_in_inna_sisters` would have to guess what it meant. So
`reasons.py` turns each key into a sentence, and those sentences are what the
model is told to explain from. The check afterwards looks for the same content,
which only works if the model was shown it in the first place.

**Nothing here is invented.** Every field was computed by a layer that can be
checked, so the same structure can be compared against the reply — the role that
went in has to be the role that comes out, and the reason has to be one that went
in at all.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sibawayh.covert import INSERTED_MARK
from sibawayh.renderers.reasons import reasons_in
from sibawayh.renderers.template import line_for
from sibawayh.schema import Token

SHOWN_FEATURES = ("aspect", "mood", "voice", "case", "state", "person", "gen", "num")
"""Which features travel with a token. The same set the CLI prints, minus
nothing: a feature that is `None` is simply left out below."""


def written_form(token: Token) -> str:
    """The word as it should appear to a student.

    `diac` rather than `form`, per CLAUDE.md, and with the inserted-token marker
    removed — the asterisk is bookkeeping and would only invite the model to
    repeat it.
    """
    return (token.diac or token.form).removesuffix(INSERTED_MARK)


def _features(token: Token) -> dict[str, str]:
    shown = {}
    for name in SHOWN_FEATURES:
        value = getattr(token.feats, name, None)
        if value is not None and value != "null":
            shown[name] = str(value)
    return shown


def token_payload(token: Token, tokens: Sequence[Token]) -> dict[str, Any]:
    """Everything the model may know about one token.

    The head travels with it because half the roles are only explicable by
    reference to it — اسم إنّ is اسم إنّ because of إنّ, and a payload without the
    head leaves the model to guess which word that was.
    """
    payload: dict[str, Any] = {
        "id": token.id,
        "word": written_form(token),
        "features": _features(token),
    }
    if token.pos:
        payload["pos"] = str(token.pos)
    if token.lemma:
        payload["lemma"] = token.lemma
    if token.irab_role:
        payload["role"] = token.irab_role
    if token.evidence:
        payload["evidence"] = list(token.evidence)
    reasons = reasons_in(token.evidence)
    if reasons:
        # The reasons travel in Arabic, not as keys. The model is asked to
        # explain from these and from nothing else, and `faithful.py` checks
        # afterwards that it did — so sending the keys alone would be asking it
        # to invent the wording of something it will then be graded on.
        payload["reasons"] = [reason.because for reason in reasons]
    if token.inserted:
        payload["covert"] = True

    head = next((other for other in tokens if other.id == token.head), None)
    if head is not None:
        payload["head"] = {"word": written_form(head), "role": head.irab_role}

    line = line_for(token)
    if line is not None:
        payload["irab"] = line
    return payload


def sentence_payload(tokens: Sequence[Token], sentence: str = "") -> dict[str, Any]:
    """The whole analysis, ready to be serialized into a prompt."""
    return {
        "sentence": sentence or " ".join(written_form(token) for token in tokens),
        "tokens": [token_payload(token, tokens) for token in tokens],
    }
