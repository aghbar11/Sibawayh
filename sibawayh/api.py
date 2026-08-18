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
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from sibawayh import __version__
from sibawayh.hints import ladder
from sibawayh.pipeline import Pipeline
from sibawayh.renderers import Renderer, describe
from sibawayh.renderers.template import TemplateRenderer
from sibawayh.schema import Sentence, Token

MAX_LENGTH = 500
"""Longer than any sentence a student types, and short enough that a paste of a
whole page cannot tie up the parser."""

CACHE_SIZE = 256

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


def _words(tokens: Sequence[Token], lines: Sequence[str | None]) -> list[Word]:
    drawn = []
    for token, line in zip(tokens, lines, strict=True):
        rungs = ladder(token)
        drawn.append(
            Word(
                id=token.id,
                form=token.form,
                diac=token.diac or token.form,
                pos=str(token.pos) if token.pos else None,
                head=token.head,
                role=token.irab_role,
                irab=line,
                hints=[rung.text for rung in rungs.rungs] if rungs else [],
                inserted=token.inserted,
                certain=token.irab_role is not None,
            )
        )
    return drawn


def analyze(text: str, llm: bool = True) -> Analysis:
    """Analyze `text` and render it. Pure enough to cache, and cached below."""
    sentence: Sentence = pipeline.analyze(text)
    renderer = _renderer(llm)
    rendering = describe(sentence.tokens, renderer)
    words = _words(sentence.tokens, rendering.lines)

    # A renderer that fell back produced the template's lines, and saying
    # "gemini" then would credit prose the model never wrote.
    template = describe(sentence.tokens, TemplateRenderer()).lines
    source = "template" if rendering.lines == template else renderer.name
    return Analysis(sentence=sentence.sentence, words=words, source=source)


@lru_cache(maxsize=CACHE_SIZE)
def _cached(text: str, llm: bool) -> Analysis:
    return analyze(text, llm)


def forget() -> None:
    """Drop the cache. For tests, and for a key that has just been added."""
    _cached.cache_clear()


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


@app.get("/health")
def health() -> Health:
    return Health(ok=True, version=__version__, loaded=pipeline.loaded)


@app.post("/analyze")
def analyze_route(request: Request) -> Analysis:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="nothing to analyze")
    return _cached(text, request.llm)
