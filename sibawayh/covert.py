"""Covert pronoun (ضمير مستتر) insertion.

Arabic routinely leaves the agent inside the verb: يقرأ الكتاب is a complete
sentence whose فاعل is a pronoun nobody typed. Every treebank ignores this —
PADT, UD and CATiB all annotate only tokens that exist — so no parser can hand
us one, and we insert it ourselves. CLAUDE.md calls it a core differentiator;
it is also the reason `Token.inserted` exists, because these tokens are free
correct attachments and must be excluded from any treebank score.

The inserted token carries person, gender and number **copied from the verb**,
which is where that information already lives, plus `case=nom` — an agent is
nominative by definition, and the verb has no case of its own to copy.

When a verb counts as needing one
---------------------------------
A verb needs a covert agent when none of its dependents could be the overt one.
Two independent signals say a dependent could be:

* `parser_label == "SBJ"` — CATiB's own judgement, "the explicit subject of a
  verb, active or passive"
* `case == nom` — the morphological signal

Either suffices, and that redundancy is deliberate: on undiacritized input CAMeL
frequently returns the wrong case (it reads الرجل in `verbal_overt_agent_01` as
accusative), while a parser can equally mislabel. Requiring both would insert
pronouns into sentences that plainly have a subject.

A dependent whose case is `unknown` also blocks insertion. That is the
abstaining direction: an unreadable case might be the agent, and a ضمير مستتر
shown to a student where none exists is a worse failure than a missing one.

Passive verbs need no special case. نائب فاعل is nominative, so it registers as
a candidate agent through exactly the same test.

Renumbering
-----------
Insertion shifts every id after it, and every head that pointed past it. Getting
this wrong silently rewires the tree, so it is done one insertion at a time
against freshly recomputed indices rather than in a single pass.
"""

from __future__ import annotations

from collections.abc import Sequence

from sibawayh.schema import ROOT_HEAD, Case, Pos, Source, Token

INSERTED_MARK = "*"
"""Suffixed to the surface form, so a reader can never mistake an inserted token
for something the student typed. `data/eval/sentences.json` writes `هو*`."""

AGENT_LABEL = "SBJ"
"""CATiB's label for an explicit subject. See `parsers/catib.py`."""

NOMINAL = frozenset({Pos.NOUN, Pos.PROPN, Pos.PRON, Pos.ADJ})
"""What can fill an agent slot. A particle or a punctuation mark cannot."""

_PRONOUNS: dict[tuple[str, str, str], str] = {
    ("1", "m", "s"): "أنا",
    ("1", "f", "s"): "أنا",
    ("1", "m", "p"): "نحن",
    ("1", "f", "p"): "نحن",
    ("2", "m", "s"): "أنت",
    ("2", "f", "s"): "أنتِ",
    ("2", "m", "d"): "أنتما",
    ("2", "f", "d"): "أنتما",
    ("2", "m", "p"): "أنتم",
    ("2", "f", "p"): "أنتن",
    ("3", "m", "s"): "هو",
    ("3", "f", "s"): "هي",
    ("3", "m", "d"): "هما",
    ("3", "f", "d"): "هما",
    ("3", "m", "p"): "هم",
    ("3", "f", "p"): "هن",
}

DEFAULT_PRONOUN = "هو"
"""Third masculine singular — the unmarked form, used when the verb's own
features are incomplete. The features on the token still say what was known."""


def pronoun_for(token: Token) -> str:
    """The pronoun that would spell out `token`'s agent, unmarked."""
    key = (token.feats.person, token.feats.gen, token.feats.num)
    if any(part is None for part in key):
        return DEFAULT_PRONOUN
    return _PRONOUNS.get((str(key[0]), str(key[1]), str(key[2])), DEFAULT_PRONOUN)


def could_be_agent(token: Token) -> bool:
    """Whether `token` might be the overt agent of the verb it hangs off.

    Deliberately generous. A false positive means we decline to insert; a false
    negative means we assert a pronoun that is not there.
    """
    if token.pos is not None and token.pos not in NOMINAL:
        return False
    if token.parser_label == AGENT_LABEL:
        return True
    return token.feats.case in {Case.NOM, Case.UNKNOWN, None}


def needs_covert_agent(verb: Token, tokens: Sequence[Token]) -> bool:
    """Whether `verb` has no dependent that could be its agent.

    A pronoun this stage inserted earlier counts as one, which is what makes
    the stage idempotent: running it twice must not give a verb two agents.
    """
    if verb.pos is not Pos.VERB:
        return False
    return not any(could_be_agent(token) for token in tokens if token.head == verb.id)


def _covert_agent(verb: Token, position: int) -> Token:
    """The token to insert under `verb`, numbered `position`."""
    return Token(
        id=position,
        form=pronoun_for(verb) + INSERTED_MARK,
        pos=Pos.PRON,
        pos_fine="pron",
        feats=verb.feats.model_copy(
            update={
                "case": Case.NOM,
                "aspect": None,
                "mood": None,
                "voice": None,
                "state": None,
            }
        ),
        head=verb.id,
        evidence=["verb_has_no_overt_agent", "features_copied_from_verb"],
        provenance={"form": Source.COVERT, "feats": Source.COVERT, "head": Source.COVERT},
        inserted=True,
    )


def _renumber(tokens: list[Token], inserted_at: int) -> list[Token]:
    """Shift ids and heads to make room for a token now sitting at `inserted_at`.

    Everything from `inserted_at` onwards moves up by one, and any head pointing
    at those tokens follows it. `ROOT_HEAD` and heads before the insertion point
    are untouched.
    """

    def shift(index: int) -> int:
        return index + 1 if index >= inserted_at else index

    return [
        token.model_copy(
            update={
                "id": shift(token.id),
                "head": None
                if token.head is None
                else (ROOT_HEAD if token.head == ROOT_HEAD else shift(token.head)),
            }
        )
        for token in tokens
    ]


def insert_covert_pronouns(tokens: Sequence[Token]) -> list[Token]:
    """Return `tokens` with a ضمير مستتر added under every agentless verb.

    Pure: the tokens handed in are not touched. Each pronoun goes immediately
    after its verb, which is where `data/eval/sentences.json` puts it and where
    a reader expects to find it.

    Only structure and morphology are set. `irab_role` stays empty — naming the
    inserted token فاعل is the rule engine's job, and this stage has no business
    pre-empting it.
    """
    result = list(tokens)
    # Left to right, re-reading ids each time: an earlier insertion renumbers
    # everything after it, so a precomputed list of positions would go stale.
    verb_index = 0
    while verb_index < len(result):
        verb = result[verb_index]
        if verb.inserted or not needs_covert_agent(verb, result):
            verb_index += 1
            continue

        position = verb.id + 1
        result = _renumber(result, position)
        result.insert(verb_index + 1, _covert_agent(verb, position))
        verb_index += 2  # skip the token just inserted
    return result
