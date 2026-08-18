"""Tests for the renderer contract.

No backend exists yet, so these drive a stub. The point is the seam itself: that
a renderer cannot touch the analysis, that declining is representable, and that a
backend returning the wrong number of lines is caught before its prose is paired
with the wrong word.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

import pytest
from sibawayh.renderers import Renderer, RenderError, Rendering, describe
from sibawayh.schema import Case, Features, Pos, Sentence, Token


def sentence_of(*forms: str) -> Sentence:
    return Sentence(
        sentence=" ".join(forms),
        tokens=[
            Token(id=position, form=form, pos=Pos.NOUN, feats=Features(case=Case.NOM))
            for position, form in enumerate(forms, start=1)
        ],
    )


class Fixed(Renderer):
    """Says the same thing about every token."""

    name = "fixed"
    deterministic = True

    def __init__(self, lines: Sequence[str | None] | None = None) -> None:
        self.lines = lines

    def render(self, tokens: Sequence[Token]) -> Rendering:
        if self.lines is not None:
            return Rendering.of(self.lines)
        return Rendering.of([f"{token.form}: مبتدأ" for token in tokens])


# --- the result type ----------------------------------------------------------------


def test_lines_are_addressed_by_token_id() -> None:
    rendering = Rendering.of(["أولى", "ثانية"])
    assert rendering.line_for(1) == "أولى"
    assert rendering.line_for(2) == "ثانية"


def test_declining_is_representable() -> None:
    rendering = Rendering.of(["أولى", None])
    assert rendering.line_for(2) is None
    assert rendering.described == 1


def test_a_blank_line_is_refused() -> None:
    """Whitespace would show the student an empty إعراب and look like a bug in
    the UI. Declining has its own spelling."""
    with pytest.raises(RenderError, match="empty line"):
        Rendering.of(["أولى", "   "])


def test_rendering_is_frozen() -> None:
    rendering = Rendering.of(["أولى"])
    with pytest.raises(dataclasses.FrozenInstanceError):
        rendering.lines = ()  # type: ignore[misc]


# --- the stage ----------------------------------------------------------------------


def test_describe_returns_one_line_per_token() -> None:
    sentence = sentence_of("الكتاب", "مفيد")
    rendering = describe(sentence.tokens, Fixed())
    assert rendering.lines == ("الكتاب: مبتدأ", "مفيد: مبتدأ")


def test_too_few_lines_is_refused() -> None:
    """Silently accepting them would pair one token's prose with another's word."""
    sentence = sentence_of("الكتاب", "مفيد")
    with pytest.raises(RenderError, match="1 lines for 2 tokens"):
        describe(sentence.tokens, Fixed(["الكتاب: مبتدأ"]))


def test_too_many_lines_is_refused() -> None:
    sentence = sentence_of("الكتاب")
    with pytest.raises(RenderError, match="2 lines for 1 tokens"):
        describe(sentence.tokens, Fixed(["أولى", "ثانية"]))


def test_describe_does_not_touch_the_tokens() -> None:
    """A renderer describes an analysis; it may not become part of one."""
    sentence = sentence_of("الكتاب", "مفيد")
    before = sentence.model_dump()
    describe(sentence.tokens, Fixed())
    assert sentence.model_dump() == before


def test_a_sentence_with_no_tokens_renders_to_nothing() -> None:
    assert describe([], Fixed()).lines == ()


# --- the contract -------------------------------------------------------------------


def test_a_renderer_must_implement_render() -> None:
    class Silent(Renderer):
        pass

    with pytest.raises(TypeError):
        Silent()  # type: ignore[abstract]


def test_backends_are_generative_unless_they_say_otherwise() -> None:
    """A model is the unpredictable case, so the default has to be the cautious one."""

    class Whatever(Renderer):
        def render(self, tokens: Sequence[Token]) -> Rendering:
            return Rendering.of([None] * len(tokens))

    assert not Whatever().deterministic
    assert Fixed().deterministic
