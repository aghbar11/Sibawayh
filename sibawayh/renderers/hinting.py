"""Letting the model say the hints, without letting it decide what a hint says.

The ladder in `hints.py` is correct and a little stiff: its wording comes from a
table, so every student gets the same sentence about every مضاف. A model can do
that part far better — warmer, and about *this* sentence rather than about the
category.

**What it may not do is choose what to reveal.** Asked to hint at اسم إنّ, a
helpful model writes *"it follows إنّ, so it is اسم إنّ منصوب"*. That is fluent,
correct, and it has just answered the question it was asked to hint at. The
teaching collapses into telling, and nothing would notice, because the output
looks better than a real hint.

So the split is the same one as everywhere else in this package. The ladder
decides **what** each rung may contain; the model decides **how** it is said; and
`faithful.leaks` checks afterwards that the answer did not appear. A rung that
leaks is thrown away and the table's wording is used instead — correct, stiff,
and not a spoiler.

**The answer rung is not sent here at all.** It is the إعراب line, and the
renderer already produces it. Asking twice would let the two disagree, and a
ladder whose last rung differs from the line beside the word is a ladder a
student stops trusting.

**One call for the whole sentence.** Three rungs times six words is eighteen
requests if each tap asks; the free tier would be gone in two sentences. Every
rung of every word comes back at once, and the caller caches it with the
analysis, so tapping through hints afterwards is free.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sibawayh.hints import ladder
from sibawayh.renderers.evidence import written_form
from sibawayh.renderers.faithful import leaks
from sibawayh.renderers.gemini import GeminiClient, GeminiError
from sibawayh.schema import Token

TEACHING_RUNGS = 2
"""How many rungs the model is given: the question and the reasoning. The third
is the answer and belongs to the renderer."""

INSTRUCTION = """أنت معلّم نحو تُرشد طالبًا إلى إعراب كلمة دون أن تخبره به.

سيصلك لكل كلمة تلميحان: سؤالٌ يوجّه نظره، ثم القرينة التي بُني عليها الإعراب.
مهمتك إعادة صياغتهما بأسلوب ودود قريب، وأن تربطهما بهذه الجملة بعينها لا
بالقاعدة العامة.

القواعد الصارمة:
- لا تذكر الموقع الإعرابي للكلمة ولا حركتها بأي حال. هذا هو الجواب، ويأتي لاحقًا.
- لا تضف قرينة من عندك؛ أعد صياغة ما وصلك فقط.
- التلميح الأول سؤال يفتح التفكير، والثاني يكشف القرينة دون أن يسمّي الجواب.
- جملة واحدة قصيرة لكل تلميح، بالعربية الفصحى، بلا رموز ولا تنسيق.
"""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "hints": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "rungs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "rungs"],
            },
        }
    },
    "required": ["hints"],
}


def _prompt(tokens: Sequence[Token]) -> str:
    sentence = " ".join(written_form(token) for token in tokens if not token.inserted)
    blocks = []
    for token in tokens:
        rungs = ladder(token)
        if rungs is None:
            continue
        question, reasoning = rungs.rungs[0].text, rungs.rungs[1].text
        blocks.append(
            f"- رقم {token.id} ({written_form(token)}):\n"
            f"    التلميح الأول: {question}\n"
            f"    التلميح الثاني: {reasoning}"
        )
    return f"الجملة: {sentence}\n\nالتلميحات المطلوب إعادة صياغتها:\n" + "\n".join(blocks)


def phrase(
    tokens: Sequence[Token],
    client: GeminiClient | None = None,
) -> dict[int, tuple[str, ...]]:
    """The model's wording for the teaching rungs, keyed by token id.

    A token appears only if every rung came back usable. Empty overall when there
    is no key, no reachable model, or nothing with a ladder — the caller then
    keeps the table's wording, which is the same hint in plainer words.
    """
    with_ladders = [token for token in tokens if ladder(token) is not None]
    if not with_ladders:
        return {}

    try:
        parsed = (client or GeminiClient()).ask(INSTRUCTION, _prompt(tokens), SCHEMA)
        offered = {int(item["id"]): list(item["rungs"]) for item in parsed["hints"]}
    except (GeminiError, KeyError, TypeError, ValueError):
        return {}

    phrased: dict[int, tuple[str, ...]] = {}
    for token in with_ladders:
        rungs = offered.get(token.id)
        if rungs is None or len(rungs) < TEACHING_RUNGS:
            continue
        wording = tuple(str(rung).strip() for rung in rungs[:TEACHING_RUNGS])
        if all(wording) and not any(leaks(rung, token) for rung in wording):
            phrased[token.id] = wording
    return phrased
