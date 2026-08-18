"""Tests for the conversation about one word.

The promise being tested is narrow and absolute: while the student has not
pressed إظهار, the tutor does not say the role or the case, however it is asked.
Everything else here is about what happens when the model tries to anyway.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sibawayh.config import ENV_FILE_VAR, forget_env_files
from sibawayh.renderers.gemini import API_KEY_ENV, GeminiClient
from sibawayh.schema import Case, Features, Gender, Number, Pos, Token
from sibawayh.tutor import (
    DEFLECTION,
    MEMORY,
    STUDENT,
    TEACHER,
    UNAVAILABLE,
    Turn,
    _about,
    answer,
)

INNA = Token(id=1, form="إن", diac="إِنَّ", pos=Pos.PART, head=0, irab_role="حرف نصب")
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
SENTENCE = [INNA, PLURAL]


@pytest.fixture(autouse=True)
def _no_real_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_FILE_VAR, str(tmp_path / "absent.env"))
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    forget_env_files()


def envelope(reply: str) -> bytes:
    inner = json.dumps({"reply": reply}, ensure_ascii=False)
    return json.dumps(
        {"candidates": [{"content": {"parts": [{"text": inner}]}}]}, ensure_ascii=False
    ).encode("utf-8")


def saying(*replies: str) -> tuple[GeminiClient, list[bytes]]:
    sent: list[bytes] = []
    remaining = [envelope(reply) for reply in replies]

    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        sent.append(body)
        return remaining.pop(0)

    return GeminiClient(api_key="k", transport=transport, sleep=lambda _: None), sent


def prompt_of(body: bytes) -> str:
    return json.loads(body.decode("utf-8"))["contents"][0]["parts"][0]["text"]


# --- what the model is not told -----------------------------------------------------


def test_the_answer_is_not_sent_while_it_is_hidden() -> None:
    """The strong half of the promise. A model cannot leak what it was never
    told, and everything after this is the weaker half."""
    told = _about(PLURAL, SENTENCE, revealed=False)
    assert "اسم إنّ" not in told
    assert "منصوب" not in told
    assert "الياء" not in told


def test_the_other_words_are_sent() -> None:
    """Knowing that إنّ before it is a حرف نصب is a clue, not the answer, and
    withholding it would leave the tutor with nothing to point at."""
    told = _about(PLURAL, SENTENCE, revealed=False)
    assert "حرف نصب" in told
    assert "إنّ أو إحدى أخواتها" in told


def test_the_answer_is_sent_once_it_has_been_shown() -> None:
    """Pretending it is a secret would make the tutor useless exactly when the
    student finally wants to talk about it."""
    told = _about(PLURAL, SENTENCE, revealed=True)
    assert "اسم إنّ منصوب" in told


def test_a_covert_pronoun_is_described_as_one() -> None:
    covert = Token(id=1, form="هو*", diac="هُوَ*", pos=Pos.PRON, inserted=True, irab_role="فاعل")
    assert "مستتر" in _about(covert, [covert], revealed=False)


# --- withholding ---------------------------------------------------------------------


def test_an_ordinary_reply_is_passed_through() -> None:
    client, _ = saying("انظر إلى الحرف الذي سبقها وما يفعله بما بعده.")
    said = answer(PLURAL, SENTENCE, [Turn(STUDENT, "لم أفهم")], client=client)
    assert said.text.startswith("انظر")
    assert not said.withheld


def test_a_reply_that_gives_the_answer_is_refused_and_retried() -> None:
    client, sent = saying("هي اسم إنّ منصوب.", "لاحظ الحرف قبلها وما يصنع بما بعده.")
    said = answer(PLURAL, SENTENCE, [Turn(STUDENT, "ما إعرابها؟")], client=client)
    assert said.text.startswith("لاحظ")
    assert not said.withheld
    assert len(sent) == 2
    assert "لا يجوز ذكره" in prompt_of(sent[1])


def test_a_model_that_insists_is_replaced() -> None:
    """The contract holds even when the model does not. Two refusals and the
    student is pointed at the button instead."""
    client, sent = saying("هي اسم إنّ.", "قلت لك: اسم إنّ منصوب.")
    said = answer(PLURAL, SENTENCE, [Turn(STUDENT, "قل لي فقط")], client=client)
    assert said.text == DEFLECTION
    assert said.withheld
    assert len(sent) == 2


def test_the_case_alone_is_enough_to_be_refused() -> None:
    client, _ = saying("الكلمة منصوبة، فكّر لماذا.", "فكّر فيما قبلها.")
    assert answer(PLURAL, SENTENCE, [], client=client).text == "فكّر فيما قبلها."


def test_nothing_is_withheld_after_the_answer_is_shown() -> None:
    """It is on the screen. Refusing to repeat it would be theatre."""
    client, _ = saying("هي اسم إنّ منصوب وعلامة نصبه الياء لأنه جمع مذكر سالم.")
    said = answer(PLURAL, SENTENCE, [], revealed=True, client=client)
    assert "اسم إنّ" in said.text
    assert not said.withheld


# --- the conversation ----------------------------------------------------------------


def test_the_history_travels_with_the_question() -> None:
    client, sent = saying("جيد، واصل.")
    answer(
        PLURAL,
        SENTENCE,
        [Turn(STUDENT, "أهي فاعل؟"), Turn(TEACHER, "انظر إلى ما قبلها."), Turn(STUDENT, "آه")],
        client=client,
    )
    prompt = prompt_of(sent[0])
    assert "أهي فاعل؟" in prompt
    assert "الطالب:" in prompt and "المعلّم:" in prompt


def test_only_the_recent_turns_travel() -> None:
    """A conversation left open in a tab must not grow into a request nobody can
    afford."""
    client, sent = saying("نعم.")
    turns = [Turn(STUDENT, f"سؤال رقم {index}") for index in range(MEMORY + 6)]
    answer(PLURAL, SENTENCE, turns, client=client)
    prompt = prompt_of(sent[0])
    assert "سؤال رقم 0" not in prompt
    assert f"سؤال رقم {MEMORY + 5}" in prompt


def test_the_first_question_needs_no_history() -> None:
    client, sent = saying("أهلًا، ما الذي حيّرك؟")
    answer(PLURAL, SENTENCE, [], client=client)
    assert "الحوار حتى الآن" not in prompt_of(sent[0])


# --- failure --------------------------------------------------------------------------


def test_no_key_says_so_plainly() -> None:
    said = answer(PLURAL, SENTENCE, [Turn(STUDENT, "؟")])
    assert said.text == UNAVAILABLE
    assert not said.withheld


def test_an_unreachable_model_says_so_plainly() -> None:
    def transport(url: str, body: bytes, headers: dict[str, str]) -> bytes:
        raise OSError("no route to host")

    client = GeminiClient(api_key="k", transport=transport, sleep=lambda _: None)
    assert answer(PLURAL, SENTENCE, [], client=client).text == UNAVAILABLE


def test_an_empty_reply_is_not_shown() -> None:
    client, _ = saying("   ")
    assert answer(PLURAL, SENTENCE, [], client=client).text == UNAVAILABLE
