"""Renderer backends behind a single interface.

Nothing outside this package knows whether the prose came from a lookup table or
from a model. That is what makes the model optional rather than load-bearing: if
it is down, over quota, or writing nonsense, the caller swaps the backend and the
student still gets an answer.

    rendering = describe(sentence, renderer)

`TemplateRenderer` is deterministic, offline, and needs no key. The model-backed
backend arrives after it, and degrades to it.
"""

from __future__ import annotations

from sibawayh.renderers.base import Renderer, RenderError, Rendering, describe

__all__ = ["RenderError", "Renderer", "Rendering", "describe"]
