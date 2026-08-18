"""The JSON API the browser talks to.

One request gives a page everything it needs to draw a sentence: the words, the
tree, the إعراب, and the hint ladder for each word. One round trip, because a
page that fetches hints separately is a page that shows a spinner every time a
student taps one.

**The response is not a `Token`.** `Token` carries `parser_label`, `provenance`,
`alternatives` and `arc_confidence` — the machinery of how an answer was reached.
A page has no use for them, and `parser_label` reaching a UI is an invitation to
draw it as the role, which is the one conflation this project keeps separate
everywhere else. So the response is a deliberately smaller shape.

**Prose is cached by sentence.** The analysis is deterministic, so the same
sentence produces the same payload every time, and asking the model again for it
would spend quota to receive what we already have. A class working through the
same thirteen sentences pays for each of them once.

**Failure is never an error page.** A model that is down or out of quota falls
back to the template line inside the renderer, and the request succeeds. The only
4xx here is an empty sentence.

**A suggestion is not a role.** Where the rules declined, the model may offer a
guess, and it arrives in `Word.suggestion` — never in `Word.role`. The two are
different fields so that nothing can confuse them, and the page is required to
draw them differently: a role is an answer, and a suggestion is something to take
to a teacher.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from sibawayh import __version__
from sibawayh.hints import ladder
from sibawayh.pipeline import Pipeline
from sibawayh.renderers import Renderer, describe
from sibawayh.renderers.hinting import phrase
from sibawayh.renderers.suggest import suggest, unclear
from sibawayh.renderers.template import TemplateRenderer
from sibawayh.schema import Sentence, Token
from sibawayh.tutor import STUDENT, TEACHER, Turn, answer

MAX_LENGTH = 500
"""Longer than any sentence a student types, and short enough that a paste of a
whole page cannot tie up the parser."""

MAX_MESSAGE = 1000
MAX_TURNS = 40
"""A conversation long enough to be worth having and bounded enough that one
tab cannot turn into a request nobody can afford."""

CACHE_SIZE = 256

PAGE = Path(__file__).parent / "web" / "index.html"
"""The whole front end. One file, no build step, and nothing to install — the
only thing it fetches is a font."""

pipeline = Pipeline()
"""The one pipeline the server holds. Warmed at startup."""


class Word(BaseModel):
    """One word, shaped for drawing rather than for analysis."""

    id: int
    form: str
    """As typed, so the student recognises it."""
    diac: str
    """Vowelled, which is what the student should be reading."""
    pos: str | None = None
    head: int | None = None
    """Which word governs this one; `0` for the word that heads the sentence.
    The arc diagram is drawn from these."""
    role: str | None = None
    """The i'rab role, and never `parser_label`. The two are different claims and
    a page that drew one as the other would be quietly wrong."""
    irab: str | None = None
    """The full line. `None` where the rules declined."""
    hints: list[str] = Field(default_factory=list)
    """The ladder, in order. The last one is the answer."""
    inserted: bool = False
    """True for a covert pronoun — a word that is not in the sentence. Drawn
    differently, because it is the one node with no text under it."""
    certain: bool = True
    """False where the rules abstained. The page greys these rather than hiding
    them: the word was reached and not analyzed, which is a different thing from
    being skipped."""
    suggestion: str | None = None
    """A model's guess, offered only where the rules declined and never anywhere
    else. Its own field on purpose: nothing downstream can mistake it for a
    derived role, because it is not the same field. The page must show it as a
    guess and say to check with a teacher — that obligation cannot be enforced
    from here, so it is tested instead."""


class Analysis(BaseModel):
    """Everything the page needs for one sentence."""

    sentence: str
    words: list[Word]
    source: str
    """Which renderer produced the prose — `template` or `gemini`. A model that
    was asked and fell back reports `template`, because that is what is on the
    page."""


class Request(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_LENGTH)
    llm: bool = True
    """Ask the model to rephrase. Falls back silently, so `True` is safe even
    with no key."""


class Message(BaseModel):
    """One thing that was said, as the page keeps it."""

    role: str = Field(pattern=f"^({STUDENT}|{TEACHER})$")
    text: str = Field(min_length=1, max_length=MAX_MESSAGE)


class Ask(BaseModel):
    """A question about one word of a sentence already analyzed.

    The sentence travels with the question rather than a session id: the analysis
    is cached, so recovering it costs nothing, and a demo that needs no session
    store is a demo that cannot lose one.
    """

    text: str = Field(min_length=1, max_length=MAX_LENGTH)
    word: int = Field(ge=1)
    messages: list[Message] = Field(default_factory=list, max_length=MAX_TURNS)
    revealed: bool = False
    """True once the student has pressed إظهار. Until then the word's role, case
    and line are not sent to the model at all."""


class Said(BaseModel):
    reply: str
    withheld: bool = False
    """True when the model gave the answer away and was replaced. The page marks
    it, so a student is not left thinking the tutor is being coy at random."""


class Health(BaseModel):
    ok: bool
    version: str
    loaded: bool
    """Whether the models are in memory. False means the next request pays for
    loading them."""


def _renderer(llm: bool) -> Renderer:
    if not llm:
        return TemplateRenderer()
    from sibawayh.renderers.gemini import GeminiRenderer

    return GeminiRenderer()


def _hints(token: Token, line: str | None, phrased: dict[int, tuple[str, ...]]) -> list[str]:
    """The ladder for one word, with the answer taken from the rendered line.

    The last rung has to be the line shown beside the word. Building it from the
    template while the line came from the model would let the two disagree, and a
    ladder whose ending differs from the answer is one a student stops trusting.
    """
    rungs = ladder(token)
    if rungs is None or line is None:
        return []
    teaching = phrased.get(token.id) or tuple(rung.text for rung in rungs.rungs[:-1])
    return [*teaching, line]


def _words(
    tokens: Sequence[Token],
    lines: Sequence[str | None],
    suggestions: dict[int, str] | None = None,
    phrased: dict[int, tuple[str, ...]] | None = None,
) -> list[Word]:
    offered = suggestions or {}
    wording = phrased or {}
    drawn = []
    for token, line in zip(tokens, lines, strict=True):
        drawn.append(
            Word(
                id=token.id,
                form=token.form,
                diac=token.diac or token.form,
                pos=str(token.pos) if token.pos else None,
                head=token.head,
                role=token.irab_role,
                irab=line,
                hints=_hints(token, line, wording),
                inserted=token.inserted,
                certain=token.irab_role is not None,
                suggestion=offered.get(token.id) if token.irab_role is None else None,
            )
        )
    return drawn


@lru_cache(maxsize=CACHE_SIZE)
def _analyzed(text: str) -> Sentence:
    """The analysis, kept because every turn of a conversation needs it again.

    Reanalyzing per turn would also let the tutor drift from the page in front of
    the student, which is worse than the cost.
    """
    return pipeline.analyze(text)


def analyze(text: str, llm: bool = True) -> Analysis:
    """Analyze `text` and render it. Pure enough to cache, and cached below."""
    sentence: Sentence = _analyzed(text)
    renderer = _renderer(llm)
    rendering = describe(sentence.tokens, renderer)

    # Asked only when there is something to ask about, so an ordinary sentence
    # costs one request and not two.
    suggestions = suggest(sentence.tokens) if llm and unclear(sentence.tokens) else {}
    phrased = phrase(sentence.tokens) if llm else {}
    words = _words(sentence.tokens, rendering.lines, suggestions, phrased)

    # A renderer that fell back produced the template's lines, and saying
    # "gemini" then would credit prose the model never wrote.
    template = describe(sentence.tokens, TemplateRenderer()).lines
    source = "template" if rendering.lines == template else renderer.name
    return Analysis(sentence=sentence.sentence, words=words, source=source)


@lru_cache(maxsize=CACHE_SIZE)
def _cached(text: str, llm: bool) -> Analysis:
    return analyze(text, llm)


def forget() -> None:
    """Drop the caches. For tests, and for a key that has just been added."""
    _cached.cache_clear()
    _analyzed.cache_clear()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the models before the first request rather than during it.

    Skippable with `SIBAWAYH_LAZY=1`, which is what the tests use: loading a
    parser to check that a route returns 422 for empty input is a minute spent
    on nothing.
    """
    if not os.environ.get("SIBAWAYH_LAZY"):
        pipeline.warm()
    yield


app = FastAPI(title="Sibawayh", version=__version__, lifespan=lifespan)


@app.get("/", include_in_schema=False)
def page() -> FileResponse:
    return FileResponse(PAGE, media_type="text/html")


@app.get("/health")
def health() -> Health:
    return Health(ok=True, version=__version__, loaded=pipeline.loaded)


@app.post("/analyze")
def analyze_route(request: Request) -> Analysis:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="nothing to analyze")
    return _cached(text, request.llm)


@app.post("/ask")
def ask_route(request: Ask) -> Said:
    """Answer one question about one word.

    The analysis is recovered rather than redone — it is cached, and a tutor that
    reanalyzed the sentence on every turn could drift from the page in front of
    the student.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="nothing to analyze")

    tokens = _analyzed(text).tokens
    token = next((candidate for candidate in tokens if candidate.id == request.word), None)
    if token is None:
        raise HTTPException(status_code=404, detail="no such word")

    said = answer(
        token,
        tokens,
        [Turn(message.role, message.text) for message in request.messages],
        revealed=request.revealed,
    )
    return Said(reply=said.text, withheld=said.withheld)
