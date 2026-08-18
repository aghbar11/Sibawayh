"""The hint ladder: the reasoning revealed one step at a time.

The product's claim is that it teaches i'rab rather than handing it over, and
this is the module where that is true or false. A student stuck on a word asks
for a hint and gets a question. If that is not enough they ask again and get the
observation the rule actually made. Only the third step is the answer.

    الطالِبِ   1. ما علاقة هذه الكلمة بالتي قبلها؟
               2. لأنها جاءت بعد مضاف، فهي مضاف إليه
               3. مضاف إليه مجرور وعلامة جره الكسرة الظاهرة على آخره

**The ladder is not written anywhere.** It is `Token.evidence`, which the rule
engine has been recording since it was built — CLAUDE.md's line that evidence is
*a list, not prose, revealed one item at a time* is what the field was for.
`reasons.py` supplies the Arabic; this module supplies the order.

**Three rungs, always.** A variable-length ladder would mean a student cannot
tell how close they are to the answer, and an interface where "one more hint"
sometimes means the answer and sometimes does not is one they stop trusting. So:
a question, then the reasoning, then the إعراب.

**No model is involved.** The ladder works offline, for free, identically every
time. A model can rephrase a rung afterwards — that is what `renderers/` is for —
but the teaching content is derived, not generated, and cannot drift.

**A word the rules abstained on has no ladder.** There is nothing to lead a
student towards, and a hint for an analysis we do not have would be a guess
dressed as teaching. `ladder` returns `None`, and the caller says the word is
unclear.
"""

from __future__ import annotations

from dataclasses import dataclass

from sibawayh.renderers.reasons import Reason, reasons_in
from sibawayh.renderers.template import line_for
from sibawayh.schema import Token

LOOK_AT_POSITION = "انظر إلى موقع الكلمة في الجملة، وإلى ما قبلها."
"""The nudge for a token whose evidence is all restatement.

`case=nom` and `pos=noun` repeat what the answer says, so a hint built from one
would give the answer away while pretending not to. Position is the thing a
student can always be asked to look at.
"""

NO_REASON = "لا توجد قرينة إضافية؛ انظر إلى الإعراب."
"""Said at the second rung when the rule recorded nothing that teaches. Honest,
and it tells the student the next tap is the answer."""


@dataclass(frozen=True)
class Hint:
    """One rung."""

    text: str
    reveals: bool = False
    """True only for the last rung. A caller that wants to warn before giving the
    answer away reads this rather than counting."""


@dataclass(frozen=True)
class Ladder:
    """The three rungs for one token, in the order they are revealed."""

    rungs: tuple[Hint, ...]

    @property
    def answer(self) -> str:
        return self.rungs[-1].text

    def upto(self, revealed: int) -> tuple[Hint, ...]:
        """The first `revealed` rungs. `0` is a student who has not asked yet."""
        return self.rungs[: max(0, revealed)]


def _question(reasons: tuple[Reason, ...]) -> str:
    """The first rung: a question pointing at the strongest observation.

    The first reason is the strongest because the rule listed its evidence in the
    order it checked it, and a rule checks the thing that decided the matter
    first.
    """
    return reasons[0].hint if reasons else LOOK_AT_POSITION


def _reasoning(reasons: tuple[Reason, ...]) -> str:
    """The second rung: everything the rule observed, joined.

    All of them, not just the first. By this point the student has already tried
    and failed once, and holding a reason back at that stage is withholding
    rather than teaching.
    """
    if not reasons:
        return NO_REASON
    return "، و".join(reason.because for reason in reasons)


def ladder(token: Token) -> Ladder | None:
    """The three rungs for `token`, or `None` where there is nothing to teach."""
    answer = line_for(token)
    if answer is None:
        return None

    reasons = reasons_in(token.evidence)
    return Ladder(
        rungs=(
            Hint(_question(reasons)),
            Hint(_reasoning(reasons)),
            Hint(answer, reveals=True),
        )
    )
