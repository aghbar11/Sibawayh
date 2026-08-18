"""A model's guess at a word the rules declined — offered, never asserted.

Everywhere else in this project the model is forbidden to decide anything. This
module is the one exception, and it is drawn as narrowly as it can be.

**Why the exception exists.** When the rules abstain, a student is shown a word
with nothing beside it. That is honest, and it is also the least useful thing the
page can do — the student came here stuck on exactly that word. A guess, clearly
labelled as a guess, with a note to check it with a teacher, is more use than
silence and less dangerous than a confident wrong answer, which is what abstention
exists to prevent.

**How the exception is contained.** Four rules, all structural rather than
promised:

* A suggestion never becomes `irab_role`. It is returned in its own map, keyed by
  token id, and the caller keeps it in its own field. Nothing downstream can
  mistake one for a derived role, because they are not the same field.
* Only tokens the rules declined are asked about. A word that has a role is never
  put in front of the model.
* Nothing is checked against it and nothing is scored with it. Evaluation reads
  `irab_role`, which this cannot touch.
* The page must mark it. That is the caller's obligation and this module cannot
  enforce it, which is the one place the containment is a promise rather than a
  type — so it is stated here and tested in the API.

**The model is told what we do know.** The rest of the sentence is analyzed, and
its roles constrain the answer: a sentence that already has a فاعل is not looking
for a second one. Sending only the unclear word would be asking for a guess about
a word in isolation, which is the worst version of this.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sibawayh.renderers.evidence import written_form
from sibawayh.renderers.gemini import GeminiClient, GeminiError
from sibawayh.schema import Token

INSTRUCTION = """أنت معلّم نحو تساعد طالبًا في إعراب جملة.

أُعربت أكثر كلمات الجملة بقواعد موثوقة، وبقيت كلمة أو أكثر لم يتضح إعرابها.
مهمتك أن تقترح إعرابًا لهذه الكلمات وحدها.

القواعد:
- انظر إلى إعراب بقية الكلمات؛ فهي تقيّد الجواب. الجملة التي فيها فاعل لا تطلب فاعلًا ثانيًا.
- اقترح موقعًا إعرابيًا واحدًا، واذكر حركته وعلامته إن استطعت، وسببه في جملة قصيرة.
- إن لم تستطع الترجيح فقل ذلك صراحة ولا تخترع.
- جملتان على الأكثر لكل كلمة، بالعربية الفصحى، بلا رموز ولا تنسيق.
- لا تكتب أنك غير متأكد في كل جملة؛ التنبيه يُعرض للطالب في الصفحة.
"""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "text": {"type": "string"},
                },
                "required": ["id", "text"],
            },
        }
    },
    "required": ["suggestions"],
}


def unclear(tokens: Sequence[Token]) -> list[Token]:
    """The tokens the rules declined. The only ones this module may ask about."""
    return [token for token in tokens if token.irab_role is None]


def _prompt(tokens: Sequence[Token]) -> str:
    known = "\n".join(
        f"- {written_form(token)}: {token.irab_role}"
        for token in tokens
        if token.irab_role is not None
    )
    asked = "\n".join(
        f"- رقم {token.id}: {written_form(token)}" + (f" (نوعها: {token.pos})" if token.pos else "")
        for token in unclear(tokens)
    )
    sentence = " ".join(written_form(token) for token in tokens if not token.inserted)
    return (
        f"الجملة: {sentence}\n\n"
        f"ما اتضح إعرابه:\n{known or '- لا شيء'}\n\n"
        f"الكلمات التي لم يتضح إعرابها:\n{asked}"
    )


def suggest(tokens: Sequence[Token], client: GeminiClient | None = None) -> dict[int, str]:
    """A proposed إعراب for each token the rules declined, keyed by token id.

    Empty when there is nothing to ask about, when there is no key, or when the
    model could not be reached — the same silence as before, which is the correct
    behaviour and not a degraded one.
    """
    asked = unclear(tokens)
    if not asked:
        return {}

    try:
        parsed = (client or GeminiClient()).ask(INSTRUCTION, _prompt(tokens), SCHEMA)
        offered = {int(item["id"]): str(item["text"]).strip() for item in parsed["suggestions"]}
    except (GeminiError, KeyError, TypeError, ValueError):
        return {}

    # A model asked about one word will sometimes answer about another, and a
    # suggestion landing on a token that already has a derived role would put a
    # guess beside an answer. Only what was asked about comes back.
    allowed = {token.id for token in asked}
    return {id: text for id, text in offered.items() if id in allowed and text}
