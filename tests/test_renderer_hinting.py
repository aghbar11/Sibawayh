"""Tests for letting the model word the hints.

All offline. The interesting half is the leak check: a model that answers the
question it was asked to hint at produces better-looking output than one that
does not, so nothing but an explicit test catches it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sibawayh.config import ENV_FILE_VAR, forget_env_files
from sibawayh.hints import ladder
from sibawayh.renderers.faithful import leaks
from sibawayh.renderers.gemini import API_KEY_ENV, GeminiClient
from sibawayh.renderers.hinting import TEACHING_RUNGS, _prompt, phrase
from sibawayh.schema import Case, Features, Gender, Number, Pos, Token

PLURAL = Token(
    id=2,
    form="العراقيين",
    diac="العِراقِيِّينَ",
    lemma="عِراقِيّ",
    pos=Pos.NOUN,
    head=1,
    irab_role="اسم إنّ",
    evidence=["head_lemma_in_inna_sisters"],
    feats=Features(case=Case.ACC, num=Number.P, gen=Gender.M),
)
INNA = Token(
    id=1,
    form="إن",
    diac="إِنَّ",
    pos=Pos.PART,
    head=0,
    irab_role="حرف نصب",
    evidence=["lemma_in_inna_sisters"],
)
SENTENCE = [INNA, PLURAL]


@pytest.fixture(autouse=True)
def _no_real_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_FILE_VAR, str(tmp_path / "absent.env"))
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    forget_env_files()


def envelope(hints: list[dict[str, object]]) -> bytes:
    inner = json.dumps({"hints": hints}, ensure_ascii=False)
    return json.dumps(
        {"candidates": [{"content": {"parts": [{"text": inner}]}}]}, ensure_ascii=False
    ).encode("utf-8")


def answering(reply: bytes) -> GeminiClient:
    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        return reply

    return GeminiClient(api_key="k", transport=transport, sleep=lambda _: None)


GOOD = [
    {"id": 1, "rungs": ["ما نوع هذه الكلمة الصغيرة في أول الجملة؟", "إنها من أخوات إنّ."]},
    {"id": 2, "rungs": ["انظر إلى الكلمة التي سبقتها مباشرة.", "إنّ تؤثر فيما بعدها."]},
]


# --- what the model is asked --------------------------------------------------------


def test_the_model_is_given_the_rungs_it_is_to_reword() -> None:
    prompt = _prompt(SENTENCE)
    assert str(ladder(PLURAL).rungs[0].text) in prompt  # type: ignore[union-attr]
    assert str(ladder(PLURAL).rungs[1].text) in prompt  # type: ignore[union-attr]


def test_the_answer_is_never_sent() -> None:
    """It is the إعراب line, which the renderer already produces. Asking twice
    would let the two disagree."""
    prompt = _prompt(SENTENCE)
    assert str(ladder(PLURAL).rungs[2].text) not in prompt


def test_one_call_covers_the_whole_sentence() -> None:
    """Three rungs times six words is eighteen requests if each tap asks, and the
    free tier would be gone in two sentences."""
    calls = []

    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        calls.append(url)
        return envelope(GOOD)

    phrase(SENTENCE, GeminiClient(api_key="k", transport=transport, sleep=lambda _: None))
    assert len(calls) == 1


# --- the leak check -----------------------------------------------------------------


def test_a_rung_that_answers_the_question_is_thrown_away() -> None:
    """The failure that looks like success: fluent, correct, and it has just told
    the student the thing they were being led towards."""
    spoiled = envelope(
        [
            {"id": 1, "rungs": ["سؤال بريء.", "قرينة بريئة."]},
            {"id": 2, "rungs": ["انظر لما قبلها.", "جاءت بعد إنّ فهي اسم إنّ منصوب."]},
        ]
    )
    phrased = phrase(SENTENCE, answering(spoiled))
    assert 1 in phrased
    assert 2 not in phrased


def test_the_case_may_not_appear_either() -> None:
    spoiled = envelope([{"id": 2, "rungs": ["سؤال.", "الكلمة هنا منصوبة بسبب ما قبلها."]}])
    assert phrase([PLURAL], answering(spoiled)) == {}


def test_the_sign_may_appear() -> None:
    """A hint that mentions الضمة is a strong hint and not the answer. Forbidding
    it would leave almost nothing sayable about an ending."""
    fine = envelope([{"id": 2, "rungs": ["انظر إلى آخر الكلمة.", "الياء هنا لها سبب."]}])
    assert 2 in phrase([PLURAL], answering(fine))


def test_our_own_wording_passes_its_own_check() -> None:
    """It would be a poor check that rejected the table it replaces."""
    for token in SENTENCE:
        rungs = ladder(token)
        assert rungs is not None
        assert not any(leaks(rung.text, token) for rung in rungs.rungs[:-1])


# --- what comes back ----------------------------------------------------------------


def test_only_the_teaching_rungs_come_back() -> None:
    phrased = phrase(SENTENCE, answering(envelope(GOOD)))
    assert len(phrased[2]) == TEACHING_RUNGS


def test_a_short_answer_is_dropped() -> None:
    short = envelope([{"id": 2, "rungs": ["سؤال فقط."]}])
    assert phrase([PLURAL], answering(short)) == {}


def test_a_blank_rung_is_dropped() -> None:
    blank = envelope([{"id": 2, "rungs": ["سؤال.", "   "]}])
    assert phrase([PLURAL], answering(blank)) == {}


def test_a_word_the_model_skipped_keeps_the_table() -> None:
    partial = envelope([GOOD[0]])
    phrased = phrase(SENTENCE, answering(partial))
    assert 1 in phrased and 2 not in phrased


# --- failure ------------------------------------------------------------------------


def test_no_key_means_the_table_is_used() -> None:
    assert phrase(SENTENCE) == {}


def test_an_unreachable_model_means_the_table_is_used() -> None:
    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        raise OSError("no route to host")

    client = GeminiClient(api_key="k", transport=transport, sleep=lambda _: None)
    assert phrase(SENTENCE, client) == {}


def test_an_unreadable_reply_means_the_table_is_used() -> None:
    assert phrase(SENTENCE, answering(b"not json")) == {}


def test_a_sentence_with_nothing_to_teach_asks_nothing() -> None:
    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        raise AssertionError("should not have been called")

    silent = Token(id=1, form="محمد", diac="مُحَمَّد", pos=Pos.NOUN)
    client = GeminiClient(api_key="k", transport=transport, sleep=lambda _: None)
    assert phrase([silent], client) == {}
