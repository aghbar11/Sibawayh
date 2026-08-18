"""A conversation about one word, with the answer withheld until it is asked for.

The hint ladder gives a student three fixed steps. This is what happens when
three steps are not what they need — when they want to say *لماذا ليست مبتدأ؟*, or
*I still do not see it*, or to try an answer and be told whether they are warm.

**The answer is withheld by not sending it.** While the student has not pressed
إظهار, the payload carries the word, its morphology, the observations the rule
made, and the roles of the *other* words — everything except this word's role,
case, sign and إعراب line. A model cannot leak what it was never told.

That is the strong half. The weak half is that it can still work the answer out:
it knows Arabic, and a noun after إنّ is not a hard puzzle. So every reply is also
leak-checked with `faithful.leaks`, exactly as the hints are. A reply that names
the role or the case is refused, retried once, and then replaced with a fixed
sentence pointing at the button. **The contract holds even when the model does
not.**

**After إظهار the withholding stops.** The answer is on the screen; pretending it
is a secret would make the tutor useless precisely when the student finally wants
to talk about the thing they now know.

**State lives with the page, not here.** The conversation is sent back each turn
and the analysis is recovered from the cache, so nothing here remembers anything
between requests. That is what keeps a demo from needing sessions, and what makes
the whole thing testable by handing it a list.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sibawayh.hints import ladder
from sibawayh.renderers.evidence import written_form
from sibawayh.renderers.faithful import leaks
from sibawayh.renderers.gemini import GeminiClient, GeminiError
from sibawayh.renderers.reasons import reasons_in
from sibawayh.renderers.template import line_for
from sibawayh.schema import Token

STUDENT = "student"
TEACHER = "teacher"

MEMORY = 12
"""How many past turns travel with a question. Long enough to follow an argument,
short enough that a conversation cannot grow into a request nobody can afford."""

DEFLECTION = "لن أذكر لك الإعراب الآن — اضغط «إظهار» متى شئت وسأشرحه لك كاملًا."
"""What is said when a reply cannot be shown. Not an apology and not an error:
the student asked for something the tutor is deliberately withholding, and the
button is where it lives."""

UNAVAILABLE = "تعذّر الوصول إلى المساعد الآن. جرّب التلميحات، أو أعد المحاولة بعد قليل."

TEACHING = """أنت معلّم نحو عربي تُحاور طالبًا يحاول أن يعرب كلمة بنفسه.

وصلك كل ما نعرفه عن الكلمة عدا إعرابها؛ فلا تعرفه، ولا يجوز لك أن تذكره.

القواعد الصارمة:
- لا تذكر الموقع الإعرابي للكلمة ولا حركتها بأي حال، ولو سألك الطالب صراحة.
- إن سألك عن الجواب مباشرة فقل له إن زر «إظهار» أمامه متى أرادَه، ثم أعطه قرينة جديدة.
- إن خمّن الطالب خطأً فلا تصحّح بذكر الصواب؛ وجّهه بسؤال أو بقرينة تكشف له خطأه.
- إن خمّن صوابًا فشجّعه واطلب منه أن يضغط «إظهار» ليتأكد.
- نوِّع في التلميح ولا تكرر ما قلته بلفظه.
- اعتمد على القرائن المرفقة، ولا تخترع قرينة من عندك.
- جوابك جملتان على الأكثر، بالعربية الفصحى، بلا رموز ولا تنسيق.
"""

EXPLAINING = """أنت معلّم نحو عربي تُحاور طالبًا اطّلع على إعراب الكلمة وأراد أن يفهمه.

وصلك التحليل كاملًا. اشرح وأجب عن أسئلته معتمدًا عليه.

القواعد:
- لا تخالف الإعراب الذي وصلك ولا تقترح غيره.
- اعتمد على القرائن المرفقة في التعليل.
- جوابك ثلاث جمل على الأكثر، بالعربية الفصحى، بلا رموز ولا تنسيق.
"""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"reply": {"type": "string"}},
    "required": ["reply"],
}


@dataclass(frozen=True)
class Turn:
    """One thing that was said."""

    role: str
    text: str


@dataclass(frozen=True)
class Reply:
    """What the tutor says back.

    `withheld` is true when a reply had to be replaced because it gave the answer
    away. The page can show that differently, and a caller counting them learns
    something about the prompt.
    """

    text: str
    withheld: bool = False


def _about(token: Token, tokens: Sequence[Token], revealed: bool) -> str:
    """Everything the model may know about this word, and no more."""
    others = "\n".join(
        f"- {written_form(other)}: {other.irab_role}"
        for other in tokens
        if other.id != token.id and other.irab_role
    )
    reasons = "\n".join(f"- {reason.because}" for reason in reasons_in(token.evidence))
    sentence = " ".join(written_form(other) for other in tokens if not other.inserted)

    lines = [
        f"الجملة: {sentence}",
        f"الكلمة موضع السؤال: {written_form(token)}",
    ]
    if token.pos:
        lines.append(f"نوعها: {token.pos}")
    if token.inserted:
        lines.append("هذه الكلمة ضمير مستتر لم يُكتب في الجملة.")
    lines.append(f"\nالقرائن التي لوحظت:\n{reasons or '- لا قرينة'}")
    lines.append(f"\nإعراب بقية الكلمات:\n{others or '- لا شيء'}")

    if revealed:
        answer = line_for(token)
        lines.append(f"\nإعراب الكلمة: {answer or 'لم يتضح'}")
    else:
        rungs = ladder(token)
        if rungs is not None:
            given = " / ".join(rung.text for rung in rungs.rungs[:-1])
            lines.append(f"\nالتلميحات التي رآها الطالب: {given}")
        lines.append("\nإعراب هذه الكلمة لم يصلك، ولا يجوز أن تذكره.")
    return "\n".join(lines)


def _conversation(turns: Sequence[Turn]) -> str:
    recent = list(turns)[-MEMORY:]
    if not recent:
        return ""
    spoken = "\n".join(
        ("الطالب: " if turn.role == STUDENT else "المعلّم: ") + turn.text for turn in recent
    )
    return f"\n\nالحوار حتى الآن:\n{spoken}"


def answer(
    token: Token,
    tokens: Sequence[Token],
    turns: Sequence[Turn],
    revealed: bool = False,
    client: GeminiClient | None = None,
) -> Reply:
    """One reply to the last thing the student said.

    Refuses twice before deflecting. A model that gave the answer away usually
    did so because the instruction was skimmed, and saying so recovers most of
    them; a second failure means it has decided to answer, and the fixed sentence
    is what keeps the promise the button makes.
    """
    prompt = _about(token, tokens, revealed) + _conversation(turns)
    instruction = EXPLAINING if revealed else TEACHING
    talk = client or GeminiClient()

    for attempt in (1, 2):
        try:
            parsed = talk.ask(instruction, prompt, SCHEMA)
            reply = str(parsed["reply"]).strip()
        except (GeminiError, KeyError, TypeError, ValueError):
            return Reply(UNAVAILABLE, withheld=False)

        if not reply:
            return Reply(UNAVAILABLE, withheld=False)
        if revealed or not leaks(reply, token):
            return Reply(reply)
        if attempt == 1:
            prompt += (
                "\n\nتنبيه: ذكرتَ في جوابك السابق ما لا يجوز ذكره."
                " أعد الجواب دون أن تسمّي الموقع الإعرابي ولا الحركة."
            )

    return Reply(DEFLECTION, withheld=True)
