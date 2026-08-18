"""Tests for the model-backed renderer.

Every one of these runs offline. The transport is injected, so what is under test
is the part that matters — what gets sent, what is accepted back, and what
happens when the model misbehaves — rather than whether Google is reachable.

The failures are the interesting half. A renderer that works when everything
works is not the claim; the claim is that a student never sees a wrong answer
because a model had a bad day.
"""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest
from sibawayh.config import ENV_FILE_VAR, forget_env_files
from sibawayh.renderers.evidence import sentence_payload, token_payload, written_form
from sibawayh.renderers.faithful import Facts, facts_of, is_faithful, missing_from
from sibawayh.renderers.gemini import (
    API_KEY_ENV,
    DEFAULT_MODEL,
    DEFAULT_MODELS,
    MODEL_ENV,
    GeminiRenderer,
)
from sibawayh.renderers.template import line_for
from sibawayh.schema import Case, Features, Gender, Number, Pos, Token

INNA = Token(id=1, form="إن", diac="إِنَّ", pos=Pos.PART, head=0, irab_role="حرف نصب")
PLURAL = Token(
    id=2,
    form="العراقيين",
    diac="العِراقِيِّينَ",
    lemma="عِراقِيّ",
    pos=Pos.NOUN,
    head=1,
    irab_role="اسم إنّ",
    evidence=["case=acc", "head_lemma_in_inna_sisters"],
    feats=Features(case=Case.ACC, num=Number.P, gen=Gender.M),
)
SENTENCE = [INNA, PLURAL]


@pytest.fixture(autouse=True)
def _no_real_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A key in a developer's `.env` must not change what these tests do — and
    must never be spent by running them."""
    monkeypatch.setenv(ENV_FILE_VAR, str(tmp_path / "absent.env"))
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    monkeypatch.delenv(MODEL_ENV, raising=False)
    forget_env_files()


def envelope(lines: list[dict[str, object]]) -> bytes:
    """A reply shaped the way Gemini shapes one."""
    inner = json.dumps({"lines": lines}, ensure_ascii=False)
    return json.dumps(
        {"candidates": [{"content": {"parts": [{"text": inner}]}}]}, ensure_ascii=False
    ).encode("utf-8")


def answering(*replies: bytes) -> tuple[GeminiRenderer, list[bytes]]:
    """A renderer that returns `replies` in order, and the record of what it sent."""
    sent: list[bytes] = []
    remaining = list(replies)

    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        sent.append(body)
        return remaining.pop(0) if remaining else remaining_error()

    def remaining_error() -> bytes:
        raise AssertionError("asked more times than there were replies")

    return GeminiRenderer(api_key="test-key", transport=transport, sleep=lambda _: None), sent


# --- what the model is shown --------------------------------------------------------


def test_the_payload_carries_the_finished_analysis() -> None:
    """The model's task is to rewrite an answer, not to find one. Handing it the
    answer is what makes that the task."""
    payload = token_payload(PLURAL, SENTENCE)
    assert payload["role"] == "اسم إنّ"
    assert payload["irab"] == line_for(PLURAL)
    assert payload["evidence"] == ["case=acc", "head_lemma_in_inna_sisters"]


def test_the_payload_carries_the_head() -> None:
    """اسم إنّ is only explicable by reference to إنّ, and without the head the
    model would have to guess which word that was."""
    assert token_payload(PLURAL, SENTENCE)["head"] == {"word": "إِنَّ", "role": "حرف نصب"}


def test_a_token_with_no_role_carries_none() -> None:
    bare = Token(id=1, form="محمد", diac="مُحَمَّد", pos=Pos.NOUN)
    payload = token_payload(bare, [bare])
    assert "role" not in payload
    assert "irab" not in payload


def test_the_covert_marker_is_not_shown_to_the_model() -> None:
    """It is bookkeeping, and showing it only invites the model to repeat it."""
    covert = Token(id=1, form="هو*", diac="هُوَ*", pos=Pos.PRON, inserted=True)
    assert written_form(covert) == "هُوَ"
    assert "*" not in json.dumps(token_payload(covert, [covert]), ensure_ascii=False)


def test_the_sentence_payload_covers_every_token() -> None:
    payload = sentence_payload(SENTENCE)
    assert [token["id"] for token in payload["tokens"]] == [1, 2]


# --- the check ----------------------------------------------------------------------


def test_the_facts_are_the_role_the_case_and_the_sign() -> None:
    assert facts_of(PLURAL) == Facts(role="اسم إنّ", case="منصوب", mark="الياء")


def test_the_template_line_passes_its_own_check() -> None:
    assert is_faithful(str(line_for(PLURAL)), PLURAL)


def test_friendlier_wording_passes() -> None:
    """Rewriting is the whole point; only the facts are held."""
    assert is_faithful(
        "هذه الكلمة اسم إنّ، وهي منصوبة، وعلامة نصبها الياء لأنها جمع مذكر سالم.",
        PLURAL,
    )


def test_diacritics_do_not_break_the_check() -> None:
    """A model writing منصوبٌ has not disagreed with منصوب, and rejecting it
    would discard a correct reply over a tanween."""
    assert is_faithful("اسمُ إنّ منصوبٌ وعلامةُ نصبِه الياءُ.", PLURAL)


def test_a_changed_case_fails() -> None:
    assert not is_faithful("اسم إنّ مرفوع وعلامة رفعه الواو.", PLURAL)


def test_a_dropped_role_fails() -> None:
    assert not is_faithful("منصوب وعلامة نصبه الياء.", PLURAL)


def test_a_changed_sign_fails() -> None:
    """The sign is the fact a careless rewrite is likeliest to get wrong."""
    assert not is_faithful("اسم إنّ منصوب وعلامة نصبه الفتحة.", PLURAL)


def test_what_was_lost_is_named() -> None:
    """So the retry can say it rather than asking again in general terms."""
    assert missing_from("منصوب فقط", facts_of(PLURAL)) == ("اسم إنّ", "الياء")


def test_a_token_with_no_role_has_no_facts_to_keep() -> None:
    bare = Token(id=1, form="محمد", diac="مُحَمَّد", pos=Pos.NOUN)
    assert facts_of(bare).stated == ()
    assert is_faithful("إعراب هذه الكلمة غير واضح.", bare)


# --- the good path ------------------------------------------------------------------


def test_a_faithful_reply_is_used() -> None:
    renderer, _ = answering(
        envelope(
            [
                {"id": 1, "text": "إِنَّ حرف نصب، وهو مبني على الفتح."},
                {"id": 2, "text": "اسم إنّ منصوب وعلامة نصبه الياء لأنه جمع مذكر سالم."},
            ]
        )
    )
    lines = renderer.render(SENTENCE).lines
    assert lines[0] == "إِنَّ حرف نصب، وهو مبني على الفتح."
    assert lines[1].startswith("اسم إنّ منصوب")


def test_the_analysis_is_sent_as_json() -> None:
    renderer, sent = answering(
        envelope(
            [{"id": 1, "text": "حرف نصب مبني على الفتح."}, {"id": 2, "text": str(line_for(PLURAL))}]
        )
    )
    renderer.render(SENTENCE)
    body = json.loads(sent[0].decode("utf-8"))
    prompt = body["contents"][0]["parts"][0]["text"]
    assert "اسم إنّ" in prompt
    assert "head_lemma_in_inna_sisters" in prompt


def test_the_key_travels_in_a_header_and_not_the_url() -> None:
    seen: dict[str, str] = {}

    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        seen.update(headers)
        seen["url"] = url
        return envelope([{"id": 1, "text": "حرف نصب."}, {"id": 2, "text": str(line_for(PLURAL))}])

    GeminiRenderer(api_key="secret", transport=transport).render(SENTENCE)
    assert seen["x-goog-api-key"] == "secret"
    assert "secret" not in seen["url"]


# --- every way it can go wrong ------------------------------------------------------


def test_no_key_falls_back_without_asking() -> None:
    asked = []

    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        asked.append(url)
        raise AssertionError("should not have been called")

    renderer = GeminiRenderer(api_key="", transport=transport)
    assert renderer.render(SENTENCE).lines == (line_for(INNA), line_for(PLURAL))
    assert not asked


def test_an_unreachable_model_falls_back() -> None:
    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        raise OSError("no route to host")

    renderer = GeminiRenderer(api_key="k", transport=transport, sleep=lambda _: None)
    assert renderer.render(SENTENCE).lines == (line_for(INNA), line_for(PLURAL))


def test_an_unreadable_reply_falls_back() -> None:
    renderer, _ = answering(b"not json at all")
    assert renderer.render(SENTENCE).lines == (line_for(INNA), line_for(PLURAL))


def test_a_reply_in_an_unexpected_shape_falls_back() -> None:
    renderer, _ = answering(json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}).encode())
    assert renderer.render(SENTENCE).lines == (line_for(INNA), line_for(PLURAL))


def test_an_unfaithful_line_is_retried_once_and_then_dropped() -> None:
    """Two calls, not three. A third recovers almost nothing and doubles the
    latency of a page a student is waiting on."""
    wrong = envelope([{"id": 1, "text": "حرف نصب."}, {"id": 2, "text": "اسم إنّ مرفوع."}])
    renderer, sent = answering(wrong, wrong)
    lines = renderer.render(SENTENCE).lines
    assert len(sent) == 2
    assert lines[1] == line_for(PLURAL)


def test_the_retry_names_what_was_lost() -> None:
    """Asking again in general terms produces another draft of the same mistake."""
    wrong = envelope([{"id": 1, "text": "حرف نصب."}, {"id": 2, "text": "اسم إنّ مرفوع."}])
    renderer, sent = answering(wrong, wrong)
    renderer.render(SENTENCE)
    second = json.loads(sent[1].decode("utf-8"))["contents"][0]["parts"][0]["text"]
    assert "الياء" in second
    assert "منصوب" in second


def test_a_retry_that_succeeds_is_used() -> None:
    wrong = envelope([{"id": 1, "text": "حرف نصب."}, {"id": 2, "text": "اسم إنّ مرفوع."}])
    right = envelope(
        [
            {"id": 1, "text": "حرف نصب مبني على الفتح."},
            {"id": 2, "text": "اسم إنّ منصوب وعلامة نصبه الياء."},
        ]
    )
    renderer, _ = answering(wrong, right)
    assert renderer.render(SENTENCE).lines[1] == "اسم إنّ منصوب وعلامة نصبه الياء."


def test_only_the_bad_line_falls_back() -> None:
    """A model that got one word wrong has not wasted the others."""
    wrong = envelope(
        [
            {"id": 1, "text": "إِنَّ حرف نصب، مبني على الفتح."},
            {"id": 2, "text": "اسم إنّ مرفوع."},
        ]
    )
    renderer, _ = answering(wrong, wrong)
    lines = renderer.render(SENTENCE).lines
    assert lines[0] == "إِنَّ حرف نصب، مبني على الفتح."
    assert lines[1] == line_for(PLURAL)


def test_a_missing_line_falls_back() -> None:
    short = envelope([{"id": 1, "text": "حرف نصب مبني على الفتح."}])
    renderer, _ = answering(short, short)
    assert renderer.render(SENTENCE).lines[1] == line_for(PLURAL)


def test_a_blank_line_falls_back() -> None:
    """`Rendering` refuses whitespace, so this would otherwise raise rather than
    degrade."""
    blank = envelope([{"id": 1, "text": "   "}, {"id": 2, "text": str(line_for(PLURAL))}])
    renderer, _ = answering(blank, blank)
    assert renderer.render(SENTENCE).lines[0] == line_for(INNA)


def test_an_empty_sentence_asks_nothing() -> None:
    asked = []

    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        asked.append(url)
        raise AssertionError("should not have been called")

    assert GeminiRenderer(api_key="k", transport=transport).render([]).lines == ()
    assert not asked


# --- configuration ------------------------------------------------------------------


def test_the_key_and_model_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(API_KEY_ENV, "from-env")
    monkeypatch.setenv(MODEL_ENV, "gemini-something-else")
    renderer = GeminiRenderer()
    assert renderer.api_key == "from-env"
    assert renderer.models == ("gemini-something-else",)


def test_naming_a_model_pins_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """Asking for one model means one model, not one and then the others."""
    assert GeminiRenderer(api_key="k", model="gemini-3.5-flash").models == ("gemini-3.5-flash",)


def test_the_models_have_a_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(MODEL_ENV, raising=False)
    assert GeminiRenderer(api_key="k").models == DEFAULT_MODELS
    assert DEFAULT_MODELS[0] == DEFAULT_MODEL


def test_an_exhausted_model_moves_to_the_next_one() -> None:
    """The free tier's quota is per model per day, so a model that has run out
    today will say so every time today, and the next model is a fresh bucket.
    Pausing for it would only make the student wait to be refused again."""
    tried: list[str] = []

    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        tried.append(url)
        if len(tried) == 1:
            raise urllib.error.HTTPError(url, 429, "quota", None, None)  # type: ignore[arg-type]
        return envelope(
            [{"id": 1, "text": "حرف نصب مبني على الفتح."}, {"id": 2, "text": str(line_for(PLURAL))}]
        )

    def never(_: float) -> None:
        raise AssertionError("should not have paused before trying the next model")

    renderer = GeminiRenderer(api_key="k", transport=transport, sleep=never)
    assert renderer.render(SENTENCE).lines[0] == "حرف نصب مبني على الفتح."
    assert DEFAULT_MODELS[0] in tried[0]
    assert DEFAULT_MODELS[1] in tried[1]


def test_a_wrong_key_is_not_retried() -> None:
    """A 403 will be a 403 again. Repeating it only makes a student wait longer
    for the same fallback."""
    tried: list[str] = []

    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        tried.append(url)
        raise urllib.error.HTTPError(url, 403, "forbidden", None, None)  # type: ignore[arg-type]

    renderer = GeminiRenderer(api_key="bad", transport=transport, sleep=lambda _: None)
    assert renderer.render(SENTENCE).lines == (line_for(INNA), line_for(PLURAL))
    assert len(tried) == 1


def test_the_backend_does_not_claim_to_be_deterministic() -> None:
    """It is not, and saying so is what stops anything caching it or asserting a
    fixed string against it."""
    assert not GeminiRenderer(api_key="k").deterministic
