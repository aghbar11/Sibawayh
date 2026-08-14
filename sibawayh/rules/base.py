"""The rule contract: evidence in, a named role out, or nothing at all.

A rule answers one question about one token — *is this a فاعل?* — and answers it
with the reasons it thinks so. Matching and evidence are the same act, which is
why `Rule.when` returns the evidence list rather than a boolean: a rule that
fired without being able to say why would be useless to the hint ladder, and the
hint ladder is the product.

Returning `None` is a first-class answer. No rule firing means the syntax is
undetermined, and CLAUDE.md is explicit that we then show morphology only. There
is deliberately no fallback rule, no default role, and nothing that fills the
shape with a guess.

Ordering is by ascending `priority`, and the first match wins. Specific rules
therefore need lower numbers than general ones — a rule that recognises اسم كان
must be consulted before one that recognises any nominative under a verb.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field

from sibawayh.schema import Token

Evidence = list[str]
"""Why a rule fired, one item at a time. The hint ladder reveals these in order,
so they run from the cheapest observation to the one that gives the answer away."""

Predicate = Callable[[Token, Token | None, Sequence[Token]], Evidence | None]
"""`(token, its head or None at the root, the whole sentence) -> evidence or None`."""


class RuleError(RuntimeError):
    """A registry was built wrong. Not a failure to find a role — that is `None`."""


@dataclass(frozen=True)
class Finding:
    """What a rule concluded about one token."""

    role: str
    rule_id: str
    evidence: Evidence = field(default_factory=list)


@dataclass(frozen=True)
class Rule:
    """One named, ordered test for one i'rab role.

    `role` is the Arabic string the student eventually reads. `rule_id` is the
    stable identifier that survives translation and gets recorded on the token,
    so a wrong answer can be traced to the rule that produced it.
    """

    id: str
    role: str
    priority: int
    when: Predicate
    description: str = ""

    def __call__(self, token: Token, head: Token | None, tokens: Sequence[Token]) -> Finding | None:
        evidence = self.when(token, head, tokens)
        if evidence is None:
            return None
        return Finding(role=self.role, rule_id=self.id, evidence=list(evidence))


class Registry:
    """Rules in priority order, consulted first-match-wins.

    Explicitly constructed rather than populated by import side effects: a
    registry that fills itself as modules happen to be imported makes rule
    ordering depend on import order, which is invisible and awful to debug.
    """

    def __init__(self, rules: Iterable[Rule] = ()) -> None:
        self._rules: list[Rule] = []
        for rule in rules:
            self.add(rule)

    def add(self, rule: Rule) -> None:
        if any(existing.id == rule.id for existing in self._rules):
            raise RuleError(f"duplicate rule id {rule.id!r}")
        self._rules.append(rule)
        self._rules.sort(key=lambda r: (r.priority, r.id))

    def __iter__(self) -> Iterator[Rule]:
        return iter(self._rules)

    def __len__(self) -> int:
        return len(self._rules)

    def __contains__(self, rule_id: object) -> bool:
        return any(rule.id == rule_id for rule in self._rules)

    def first_match(
        self, token: Token, head: Token | None, tokens: Sequence[Token]
    ) -> Finding | None:
        """The conclusion of the first rule that fires, or `None` to abstain."""
        for rule in self._rules:
            finding = rule(token, head, tokens)
            if finding is not None:
                return finding
        return None
