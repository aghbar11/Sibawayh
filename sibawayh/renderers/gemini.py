"""A renderer backed by Google's Gemini Flash.

Same interface as the template renderer, and a strictly smaller job than it
looks: the template has already produced the correct line for every token, and
this backend is asked to say those lines again in warmer, more explanatory Arabic
for a student who is learning. It never analyzes anything. The payload it
receives is the finished analysis — see `evidence.py` — and every reply is
checked against that analysis before anyone sees it.

**Three ways it can fail, and all three end the same way.** The network can be
down or the key wrong; the reply can be unparseable or the wrong length; a line
can quietly drop the role or change the case. Each falls back to the template
line for the affected token, so the worst outcome is prose that reads like a
textbook instead of like a teacher. A wrong answer is not among the outcomes.

**The free tier is busy, so a temporary failure is retried.** Measured against
the real endpoint: `503 UNAVAILABLE — this model is currently experiencing high
demand` comes back often enough that a single attempt loses the feature for no
reason. Three attempts with a doubling pause, and only for statuses that mean
*ask again* — a 400 or a 403 is a wrong request or a wrong key, and repeating it
only makes a student wait longer for the same fallback.

**The retry is for the whole sentence and happens once.** A model that dropped a
role usually did so because the instruction was skimmed, and asking again with
the failures named recovers most of them. Asking a third time recovers almost
nothing and doubles the latency of a page a student is waiting on.

**No SDK.** One POST to one endpoint, over `urllib`, so this adds no dependency
and no licence question to a project that already tracks both carefully. The
transport is injectable, which is what lets every test here run offline.

The key comes from `$GEMINI_API_KEY`, or from a `.env` file if that is where it
was put — see `config.py`. It travels in a header and never in the URL, so it
does not end up in a proxy log.
"""

from __future__ import annotations

import json
import time
import urllib.request
from collections.abc import Callable, Sequence
from typing import Any

from sibawayh.config import setting
from sibawayh.renderers.base import Renderer, Rendering
from sibawayh.renderers.evidence import sentence_payload
from sibawayh.renderers.faithful import facts_of, is_faithful, missing_from
from sibawayh.renderers.template import line_for
from sibawayh.schema import Token

API_KEY_ENV = "GEMINI_API_KEY"
MODEL_ENV = "SIBAWAYH_GEMINI_MODEL"
DEFAULT_MODELS = ("gemini-flash-lite-latest", "gemini-3.1-flash-lite", "gemini-3.5-flash")
"""Which models to try, in order, and why not the obvious one.

The free tier's quota is **per model per day**, and `gemini-flash-latest` is an
alias onto the newest model, which has the smallest allowance of any of them —
measured at 20 requests a day. A lite model is both the right size for this job,
which is rephrasing rather than reasoning, and far more generous.

The list is swept rather than fixed because the allowances are separate buckets:
a model that has run out today says so, and the next one has its own. That is
what makes a demo survive an afternoon of use.
"""

DEFAULT_MODEL = DEFAULT_MODELS[0]
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT = 60.0

TRANSIENT_STATUS = frozenset({408, 429, 500, 502, 503, 504})
"""Statuses that mean *ask again*, not *stop asking*.

Measured, not guessed: the free tier answers `503 UNAVAILABLE — this model is
currently experiencing high demand` often enough that a single attempt loses the
feature for no reason. A 400 or a 403 is a wrong request or a wrong key and
repeating it only wastes the student's time.
"""

ATTEMPTS = 3
BACKOFF = 1.0
"""Seconds before the second attempt, doubled before the third. Bounded at three
because a page is waiting: past that, the template line is the better answer."""

INSTRUCTION = """أنت مساعد في تعليم الإعراب لطالب مبتدئ.

سيصلك تحليل نحوي كامل وجاهز لكل كلمة في الجملة: موقعها الإعرابي، وحركتها،
وعلامتها، والقرائن التي بُني عليها التحليل، وسطر الإعراب المختصر.

مهمتك أن تعيد كتابة سطر الإعراب لكل كلمة بأسلوب ودود يشرح للطالب، لا أن تحلل
من جديد.

القواعد:
- لا تغيّر الموقع الإعرابي ولا الحركة ولا العلامة. أعد ذكرها كما وصلتك.
- اذكر السبب من قائمة الأسباب المرفقة مع الكلمة، وأعد صياغته بأسلوبك.
- لا تذكر سببًا من عندك. إن لم تصلك أسباب فاكتفِ بالإعراب.
- إن لم يصلك إعراب لكلمة، فقل إن إعرابها غير واضح، ولا تخترع لها إعرابًا،
  ثم اطلب من التلميذ أن يأخذ هذه الجملة لمدرسه.
- جملتان على الأكثر لكل كلمة، بالعربية الفصحى، بلا رموز ولا تنسيق.
"""

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "lines": {
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
    "required": ["lines"],
}

Transport = Callable[[str, bytes, dict[str, str]], bytes]
"""How a request reaches the network. Replaced in tests, and the reason nothing
here needs a key to be exercised."""


class GeminiError(RuntimeError):
    """The model could not be reached or did not answer usably.

    Raised inside this module and caught inside it. Callers see a `Rendering`
    that fell back, never an exception — a renderer failing is not a reason for a
    student to see an error page.
    """


def _post(url: str, body: bytes, headers: dict[str, str]) -> bytes:
    """The default transport. Failures are left to raise as themselves — the
    caller converts them, so every transport is covered by the same net."""
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return bytes(response.read())


def _text_of(envelope: dict[str, Any]) -> str:
    """The model's answer, out of Gemini's envelope."""
    try:
        return str(envelope["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError) as shape:
        raise GeminiError(f"unexpected reply shape: {shape}") from shape


def _lines_by_id(text: str) -> dict[int, str]:
    try:
        parsed = json.loads(text)
        return {int(line["id"]): str(line["text"]) for line in parsed["lines"]}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as bad:
        raise GeminiError(f"could not read the reply as JSON: {bad}") from bad


def _complaint(tokens: Sequence[Token], lines: dict[int, str]) -> str | None:
    """What to say on the retry, or `None` if there is nothing to complain about.

    Naming the specific losses is what makes one retry worth making. "Do it
    again" produces another draft of the same mistake.
    """
    problems = []
    for token in tokens:
        reply = lines.get(token.id)
        if reply is None:
            problems.append(f"- الكلمة رقم {token.id}: لم يصل لها سطر.")
            continue
        lost = missing_from(reply, facts_of(token))
        if lost:
            problems.append(f"- الكلمة رقم {token.id}: سقط منها " + "، ".join(lost) + ".")
    if not problems:
        return None
    return "أعد المحاولة. في إجابتك السابقة:\n" + "\n".join(problems)


class GeminiRenderer(Renderer):
    """Rewrites the template's lines as teaching prose, and never as analysis.

    `deterministic` is False, which is the honest value and has consequences:
    nothing caches this and no test asserts a fixed string against it.
    """

    name = "gemini"
    deterministic = False

    def __init__(
        self,
        api_key: str | None = None,
        model: str | Sequence[str] | None = None,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        # `None` means look it up; `""` means there deliberately is not one, and
        # the two have to be told apart or a caller can never say "do not call
        # out" while a key happens to be sitting in a .env file.
        self.api_key = setting(API_KEY_ENV) if api_key is None else api_key
        named = model or setting(MODEL_ENV)
        self.models: tuple[str, ...] = (
            DEFAULT_MODELS if not named else (named,) if isinstance(named, str) else tuple(named)
        )
        self.transport = transport or _post
        self.sleep = sleep

    def _send(self, body: bytes, headers: dict[str, str]) -> bytes:
        """One request, tried against each model in turn and then again after a pause.

        Two different failures are being handled by one loop. A model that has
        spent its daily allowance will say so every time today, so there is no
        point pausing for it — the next model is a separate bucket and answers
        immediately. A congested model will answer in a moment, so after the
        sweep comes a pause and another sweep.

        A congested endpoint and a wrong key both arrive as an `OSError`, and the
        status code is what separates them: repeating a 403 can never work, while
        giving up on a 503 throws away a request that would have. A transport
        that raises without a status — a DNS failure, a dropped connection — is
        treated as temporary, because those usually are.
        """
        delay = BACKOFF
        failure: Exception | None = None
        for attempt in range(1, ATTEMPTS + 1):
            for model in self.models:
                try:
                    return self.transport(ENDPOINT.format(model=model), body, headers)
                except (OSError, TimeoutError) as raised:
                    status = getattr(raised, "code", None)
                    if status is not None and status not in TRANSIENT_STATUS:
                        raise GeminiError(f"could not reach the model: {raised}") from raised
                    failure = raised
            if attempt < ATTEMPTS:
                self.sleep(delay)
                delay *= 2
        raise GeminiError(f"could not reach the model: {failure}") from failure

    def _ask(self, prompt: str) -> dict[int, str]:
        if not self.api_key:
            raise GeminiError(f"no API key; set ${API_KEY_ENV}")
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": INSTRUCTION}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": RESPONSE_SCHEMA,
                },
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {"content-type": "application/json", "x-goog-api-key": self.api_key}
        raw = self._send(body, headers)
        try:
            envelope = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as bad:
            raise GeminiError(f"could not read the response: {bad}") from bad
        return _lines_by_id(_text_of(envelope))

    def render(self, tokens: Sequence[Token]) -> Rendering:
        """One line per token: the model's where it kept the facts, ours where it
        did not."""
        template = [line_for(token) for token in tokens]
        if not tokens:
            return Rendering.of(template)

        prompt = json.dumps(sentence_payload(tokens), ensure_ascii=False, indent=2)
        try:
            lines = self._ask(prompt)
            complaint = _complaint(tokens, lines)
            if complaint is not None:
                lines = self._ask(prompt + "\n\n" + complaint)
        except GeminiError:
            return Rendering.of(template)

        return Rendering.of(
            [
                _kept(lines.get(token.id), token) or fallback
                for token, fallback in zip(tokens, template, strict=True)
            ]
        )


def _kept(reply: str | None, token: Token) -> str | None:
    """The model's line if it may be shown, otherwise `None` so the caller falls
    back."""
    if reply is None or not reply.strip():
        return None
    return reply.strip() if is_faithful(reply, token) else None
