"""The last check before a student sees anything: is this analysis coherent?

Rules fire one token at a time and each is blind to the others. Nothing in the
rule layer notices that a verb ended up with two agents, that a مبتدأ was handed
an accusative, or that the tree the parser produced has no root at all. Those
are properties of the whole sentence, and this is where they are checked.

A validator **never repairs anything.** It passes or it fails. On failure the
sentence downgrades to morphology-only — diacritized forms, part of speech,
features, and an honest statement that the syntax is uncertain. CLAUDE.md is
explicit that confidently wrong i'rab is the failure that kills the product, and
a contradiction is exactly the state in which we do not know which of the two
claims to keep. Dropping whichever one we happen to suspect would be a guess.

The whole sentence goes, not the offending token. A مبتدأ and its خبر are
derived from each other — `PREDICATE_SINGLE` asks whether its head is the
مبتدأ — so a wrong role does not stay local, and there is no principled way to
decide how far the damage spread.

Abstention is not failure. Most tokens on undiacritized input carry no role at
all, and that is the system working. These checks only ever fire on two claims
that *contradict*, never on a claim that is simply missing.

    result = validate(tokens)      # component: what is wrong, if anything
    tokens = enforce(tokens)       # stage: validate, and downgrade if it failed
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from sibawayh.schema import ROOT_HEAD, Case, Pos, Token

ROLES = frozenset(
    {
        # الفعل
        "فعل ماضٍ",
        "فعل ماضٍ مبني للمجهول",
        "فعل ماضٍ ناقص",
        "فعل مضارع مرفوع",
        "فعل مضارع منصوب",
        "فعل مضارع مجزوم",
        # عمدتا الجملة الفعلية وما يتعلق بهما
        "فاعل",
        "فاعل — ضمير مستتر",
        "نائب فاعل",
        "مفعول به",
        # الجملة الاسمية
        "مبتدأ",
        "مبتدأ — مضاف",
        "خبر",
        "خبر — جملة فعلية",
        "حرف جر — خبر شبه جملة",
        "ظرف مكان — خبر شبه جملة",
        # النواسخ
        "اسم كان",
        "خبر كان",
        "اسم إنّ",
        "خبر إنّ",
        # التوابع والمجرورات
        "صفة",
        "مضاف إليه",
        "مجرور",
        # الحروف
        "حرف جزم",
        "حرف نصب",
    }
)
"""Every role string this system is allowed to put in front of a student.

Written out by hand rather than collected from the registry, which is the only
thing that makes the check worth running: a typo in a rule's `role`, or a rule
that quietly invents a grammatical term, has to disagree with *something*. An
inventory derived from the rules could not disagree with the rules.

Smaller than the I3rab paper's 34 labels. حال، تمييز، بدل، توكيد، عطف، مفعول
مطلق have no rules yet, and a label with nothing producing it would only mask
the next typo. They arrive with the rules that emit them.
"""

AGENT_ROLES = frozenset({"فاعل", "فاعل — ضمير مستتر", "نائب فاعل", "اسم كان"})
"""The roles that fill a verb's subject slot.

نائب فاعل is what a فاعل is called under the passive, and اسم كان what it is
called under a defective verb. One slot under three names, and a verb has
exactly one of it.
"""

ROLE_CASE: dict[str, Case] = {
    "مبتدأ": Case.NOM,
    "مبتدأ — مضاف": Case.NOM,
    "خبر": Case.NOM,
    "فاعل": Case.NOM,
    "فاعل — ضمير مستتر": Case.NOM,
    "نائب فاعل": Case.NOM,
    "اسم كان": Case.NOM,
    "خبر إنّ": Case.NOM,
    "مفعول به": Case.ACC,
    "خبر كان": Case.ACC,
    "اسم إنّ": Case.ACC,
    "مضاف إليه": Case.GEN,
    "مجرور": Case.GEN,
}
"""Roles whose case the role itself fixes, and what it has to be.

Left out on purpose: صفة, whose case is copied from the noun it follows rather
than fixed by the role; and every verb and particle role, which have no case to
disagree about.
"""

MAX_DEPTH = 200
"""Cycle guard. Longer than any sentence a student will type, so a walk that
runs past it is a loop, not a deep tree."""


@dataclass(frozen=True)
class Violation:
    """One contradiction, named by the check that found it.

    `token_ids` holds the tokens involved — both of them where two claims
    disagree — so a caller can point at the problem rather than only report that
    there is one.
    """

    check: str
    message: str
    token_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class ValidationResult:
    """What the checks found. Empty means the analysis may be shown as it stands."""

    violations: tuple[Violation, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.violations

    @property
    def checks_failed(self) -> tuple[str, ...]:
        """The distinct check names that fired, in the order they fired."""
        seen: dict[str, None] = {}
        for violation in self.violations:
            seen.setdefault(violation.check, None)
        return tuple(seen)

    def __bool__(self) -> bool:
        return self.ok


# --- the checks ---------------------------------------------------------------------


def _dependents(tokens: Sequence[Token], head: Token) -> list[Token]:
    return [token for token in tokens if token.head == head.id]


def check_tree(tokens: Sequence[Token]) -> Iterator[Violation]:
    """Exactly one root, every head a real token, and no cycles.

    A malformed tree is not a wrong answer so much as an undrawable one: the UI
    walks these arcs to lay the sentence out, and the rule engine walks them to
    ask what a token's عامل is.
    """
    if not tokens:
        return

    ids = {token.id for token in tokens}

    unattached = [token.id for token in tokens if token.head is None]
    if unattached:
        yield Violation(
            "tree.unattached",
            f"tokens {unattached} have no head; the parser has not run on them",
            tuple(unattached),
        )

    dangling = [
        token.id
        for token in tokens
        if token.head is not None and token.head != ROOT_HEAD and token.head not in ids
    ]
    if dangling:
        yield Violation(
            "tree.dangling_head",
            f"tokens {dangling} point at a head that is not in the sentence",
            tuple(dangling),
        )

    roots = [token.id for token in tokens if token.head == ROOT_HEAD]
    if len(roots) != 1:
        yield Violation(
            "tree.root_count",
            f"a sentence has exactly one root; found {len(roots)} {roots}",
            tuple(roots),
        )

    if unattached or dangling:
        # Walking arcs that do not resolve would raise rather than report.
        return

    by_id = {token.id: token for token in tokens}
    for token in tokens:
        seen: set[int] = set()
        current = token
        for _ in range(MAX_DEPTH):
            head = current.head
            if head == ROOT_HEAD:
                break
            if current.id in seen:
                yield Violation(
                    "tree.cycle",
                    f"token {token.id} never reaches the root; the arcs loop",
                    (token.id,),
                )
                break
            seen.add(current.id)
            current = by_id[head]
        else:
            yield Violation(
                "tree.cycle",
                f"token {token.id} is more than {MAX_DEPTH} arcs from the root",
                (token.id,),
            )


def check_roles_are_known(tokens: Sequence[Token]) -> Iterator[Violation]:
    """Every role we emit is one we meant to emit.

    Catches a rule whose `role` string drifted from the inventory — a typo, a
    missing shadda on إنّ, an em dash that became a hyphen. The student reads
    this as a grammatical term, so it has to be one.
    """
    for token in tokens:
        if token.irab_role is not None and token.irab_role not in ROLES:
            yield Violation(
                "role.unknown",
                f"token {token.id} was labelled {token.irab_role!r}, "
                f"which is not in the role inventory",
                (token.id,),
            )


def check_one_agent_per_verb(tokens: Sequence[Token]) -> Iterator[Violation]:
    """A verb has exactly one فاعل — never two, and never none.

    Two is always a contradiction, and it is the shape the covert-pronoun bug
    took: inserting a ضمير مستتر under a verb that already had an overt subject.

    None is a contradiction only when every dependent of the verb was labelled
    something else. If any of them abstained, the agent may well be that one,
    and an abstention is not an error. Undiacritized input abstains constantly,
    so treating every missing agent as failure would downgrade nearly everything.
    """
    for verb in tokens:
        if verb.pos is not Pos.VERB:
            continue
        dependents = _dependents(tokens, verb)
        agents = [token for token in dependents if token.irab_role in AGENT_ROLES]

        if len(agents) > 1:
            yield Violation(
                "agent.multiple",
                f"verb {verb.id} ({verb.form}) has {len(agents)} agents: "
                f"{[token.form for token in agents]}",
                (verb.id, *(token.id for token in agents)),
            )
        elif not agents and dependents and all(t.irab_role is not None for t in dependents):
            yield Violation(
                "agent.missing",
                f"verb {verb.id} ({verb.form}) has no agent, and every dependent "
                f"was labelled something else",
                (verb.id, *(token.id for token in dependents)),
            )


def check_case_agrees_with_role(tokens: Sequence[Token]) -> Iterator[Violation]:
    """A role that fixes a case must not sit on a token whose case says otherwise.

    Only a definite disagreement counts. `unknown`, `null` and unset are silence,
    and filling silence from structure is deliberate — it is what lets a bare
    محمد be a مبتدأ. Contradicting morphology that actually spoke is not.
    """
    for token in tokens:
        required = ROLE_CASE.get(token.irab_role or "")
        actual = token.feats.case
        if required is None or actual not in {Case.NOM, Case.ACC, Case.GEN}:
            continue
        if actual is not required:
            yield Violation(
                "case.disagrees",
                f"token {token.id} ({token.form}) is {token.irab_role}, which is "
                f"{required.value}, but morphology reads {actual.value}",
                (token.id,),
            )


CHECKS = (
    check_tree,
    check_roles_are_known,
    check_one_agent_per_verb,
    check_case_agrees_with_role,
)
"""All of them run, in this order. A caller deciding what to show is better
served by every contradiction than by the first one."""


# --- the component, and the stage ---------------------------------------------------


def validate(tokens: Sequence[Token]) -> ValidationResult:
    """Every contradiction in the analysis, or an empty result if there are none."""
    return ValidationResult(tuple(violation for check in CHECKS for violation in check(tokens)))


def strip_syntax(tokens: Sequence[Token]) -> list[Token]:
    """Return `tokens` with every derived role removed and morphology untouched.

    Heads stay: an arc is the parser's claim, not ours, and the UI still needs
    somewhere to hang the words even when we decline to name what they do.

    `evidence` stays too. Every item in it is an observation — `case=acc`,
    `head_pos=verb`, `verb_has_no_overt_agent` — and observations do not become
    false because the conclusion drawn from them was thrown away. What goes is
    the conclusion: the role, the rule that produced it, and its provenance.
    """
    return [
        token.model_copy(
            update={
                "irab_role": None,
                "rule_id": None,
                "confidence": None,
                "provenance": {
                    key: value for key, value in token.provenance.items() if key != "irab_role"
                },
            }
        )
        for token in tokens
    ]


def enforce(tokens: Sequence[Token]) -> list[Token]:
    """The pipeline stage: keep the analysis if it holds together, drop it if not.

    Pure, and `(list[Token]) -> list[Token]` like every other stage. A caller
    that needs to say *why* the syntax vanished calls `validate` itself — this
    returns tokens, and a token has no room for a sentence-level verdict.
    """
    return list(tokens) if validate(tokens).ok else strip_syntax(tokens)
