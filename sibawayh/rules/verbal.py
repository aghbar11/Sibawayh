"""Verbal sentence rules: the verb itself, فاعل، نائب فاعل، مفعول به.

Two exclusions run through everything here, and both are about *not* answering:

**كان وأخواتها are not complete verbs.** They raise their اسم and put their خبر
in the accusative, so a nominative under كان is اسم كان and an accusative is
خبر كان — neither is فاعل or مفعول به. Those roles belong to `nawasikh.py`,
which does not exist yet, so every rule here excludes النواسخ *itself* rather
than deferring to a file that cannot yet outrank it. Deferring would mean
shipping a confident wrong answer in the meantime.

**A verb can be a خبر.** In محمد يقرأ الكتاب the verb is the predicate of a
مبتدأ, and gold names it خبر — جملة فعلية, not فعل مضارع مرفوع. So the rules
that name a verb's own form only fire when the verb heads its clause: at the
root, or under a governing particle like لم. A verb hanging off a nominal is
left for `nominal.py`.

The verb's own role is a composed string — aspect, then voice, then mood — and
it ships as one rule per combination rather than one rule with a computed role.
Five explicit rules cost a few lines and buy a distinct `rule_id` per form, so a
wrong answer names the exact rule that produced it and the hint text can differ
per form. A passive imperfect has no rule: gold has no example, and inventing
the string would be a guess.
"""

from __future__ import annotations

from collections.abc import Sequence

from sibawayh.rules.base import Evidence, Rule
from sibawayh.rules.lexicon import is_defective_verb
from sibawayh.schema import Aspect, Case, Mood, Pos, Token, Voice

NOMINAL = frozenset({Pos.NOUN, Pos.PROPN, Pos.PRON, Pos.ADJ})

PRD = "PRD"
"""CATiB's label for the complement of كان وأخواتها and إنّ وأخواتها. A second,
independent signal that a head is a ناسخ — see `parsers/catib.py`."""


def _heads_its_clause(verb: Token, head: Token | None) -> bool:
    """Whether `verb` is the verb of its own sentence rather than a predicate.

    True at the root, and under a governing particle (لم يقرأ). False under a
    nominal, which makes the verb a خبر.
    """
    return head is None or head.pos is Pos.PART


def _is_complete_verb(token: Token | None) -> bool:
    """A فعل تام — a verb that takes a فاعل, not a ناسخ that takes an اسم."""
    return token is not None and token.pos is Pos.VERB and not is_defective_verb(token)


def _governs_a_predicate(verb: Token, tokens: Sequence[Token]) -> bool:
    """Whether any dependent is labelled `PRD`, which only النواسخ take."""
    return any(token.head == verb.id and token.parser_label == PRD for token in tokens)


def _verb_form(aspect: Aspect | None, mood: Mood | None, voice: Voice | None):
    """Build the predicate for one verb form, guarding the exclusions above."""

    def when(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
        if token.pos is not Pos.VERB or not _heads_its_clause(token, head):
            return None
        if is_defective_verb(token) or _governs_a_predicate(token, tokens):
            return None
        # CAMeL fills `mood` on perfect verbs too — كتب comes back
        # aspect=perfect *and* mood=indicative — so a rule keyed on mood alone
        # would claim a past-tense verb as مضارع. Aspect is checked either way.
        if aspect is Aspect.PERFECT and token.feats.aspect is not Aspect.PERFECT:
            return None
        if aspect is Aspect.IMPERFECT and token.feats.aspect is Aspect.PERFECT:
            return None
        if mood is not None and token.feats.mood is not mood:
            return None
        # An unstated voice means active; an explicitly passive verb needs its
        # own rule, and there is none for the imperfect.
        actual = token.feats.voice
        if voice is Voice.PASSIVE and actual is not Voice.PASSIVE:
            return None
        if voice is not Voice.PASSIVE and actual is Voice.PASSIVE:
            return None

        evidence = ["pos=verb", "heads_the_clause"]
        if aspect is not None:
            evidence.append(f"aspect={aspect}")
        if mood is not None:
            evidence.append(f"mood={mood}")
        if voice is Voice.PASSIVE:
            evidence.append("voice=passive")
        return evidence

    return when


def _argument(case: Case, *, passive_head: bool):
    """Build the predicate for a nominal argument of a complete verb."""

    def when(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
        if token.pos not in NOMINAL or not _is_complete_verb(head):
            return None
        assert head is not None  # narrowed by _is_complete_verb
        if _governs_a_predicate(head, tokens) or token.parser_label == PRD:
            return None
        if token.feats.case is not case:
            return None
        head_is_passive = head.feats.voice is Voice.PASSIVE
        if head_is_passive is not passive_head:
            return None

        evidence = [f"case={case}", "head_pos=verb", f"head_form={head.form}"]
        evidence.append("head_voice=passive" if passive_head else "head_voice=active")
        return evidence

    return when


VERB_PERFECT_ACTIVE = Rule(
    id="VERB_PERFECT_ACTIVE",
    role="فعل ماضٍ",
    priority=100,
    when=_verb_form(Aspect.PERFECT, None, Voice.ACTIVE),
    description="A perfect verb heading its clause.",
)

VERB_PERFECT_PASSIVE = Rule(
    id="VERB_PERFECT_PASSIVE",
    role="فعل ماضٍ مبني للمجهول",
    priority=95,
    when=_verb_form(Aspect.PERFECT, None, Voice.PASSIVE),
    description="A perfect verb in the passive voice.",
)

VERB_IMPERFECT_INDICATIVE = Rule(
    id="VERB_IMPERFECT_INDICATIVE",
    role="فعل مضارع مرفوع",
    priority=100,
    when=_verb_form(Aspect.IMPERFECT, Mood.INDICATIVE, Voice.ACTIVE),
    description="An imperfect verb with nothing governing its mood.",
)

VERB_IMPERFECT_SUBJUNCTIVE = Rule(
    id="VERB_IMPERFECT_SUBJUNCTIVE",
    role="فعل مضارع منصوب",
    priority=100,
    when=_verb_form(Aspect.IMPERFECT, Mood.SUBJUNCTIVE, Voice.ACTIVE),
    description="An imperfect verb put in the subjunctive by a ناصب such as لن.",
)

VERB_IMPERFECT_JUSSIVE = Rule(
    id="VERB_IMPERFECT_JUSSIVE",
    role="فعل مضارع مجزوم",
    priority=100,
    when=_verb_form(Aspect.IMPERFECT, Mood.JUSSIVE, Voice.ACTIVE),
    description="An imperfect verb put in the jussive by a جازم such as لم.",
)


def _covert_agent(token: Token, head: Token | None, tokens: Sequence[Token]) -> Evidence | None:
    """An inserted pronoun hanging off a verb — a فاعل by construction."""
    if not token.inserted or token.pos is not Pos.PRON:
        return None
    if head is None or head.pos is not Pos.VERB:
        return None
    return ["inserted_by_us", "head_pos=verb", "verb_has_no_overt_agent"]


COVERT_AGENT = Rule(
    id="COVERT_AGENT",
    role="فاعل — ضمير مستتر",
    priority=10,
    when=_covert_agent,
    description="An inserted pronoun under a verb is its agent; that is why it was inserted.",
)

VERBAL_AGENT = Rule(
    id="VERBAL_AGENT",
    role="فاعل",
    priority=110,
    when=_argument(Case.NOM, passive_head=False),
    description="The nominative argument of an active complete verb.",
)

PASSIVE_AGENT = Rule(
    id="PASSIVE_AGENT",
    role="نائب فاعل",
    priority=105,
    when=_argument(Case.NOM, passive_head=True),
    description="The nominative argument of a passive verb — voice is the discriminator.",
)

VERBAL_OBJECT = Rule(
    id="VERBAL_OBJECT",
    role="مفعول به",
    priority=110,
    when=_argument(Case.ACC, passive_head=False),
    description="The accusative argument of an active complete verb.",
)

VERBAL_RULES = (
    COVERT_AGENT,
    VERB_PERFECT_PASSIVE,
    VERB_PERFECT_ACTIVE,
    VERB_IMPERFECT_INDICATIVE,
    VERB_IMPERFECT_SUBJUNCTIVE,
    VERB_IMPERFECT_JUSSIVE,
    PASSIVE_AGENT,
    VERBAL_AGENT,
    VERBAL_OBJECT,
)
