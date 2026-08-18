"""Tests for the JSON API.

None of these load a model. The pipeline is replaced with one that returns gold
analyses, which is what the API would have produced anyway and takes no minute to
do it. What is under test is the shape the page receives and the promises made
about it — not whether the parser works, which has its own tests.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import sibawayh.api as api
from fastapi.testclient import TestClient
from sibawayh.renderers.base import Renderer, Rendering
from sibawayh.schema import Sentence, Token

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))
GOLD = {record["sentence"]: Sentence.model_validate(record) for record in EVAL["sentences"]}

INNA = "إن العراقيين قادرون"
COVERT = "محمد يقرأ الكتاب"


class GoldPipeline:
    """Answers from the eval set, and loads nothing."""

    loaded = True
    asked: list[str]

    def __init__(self) -> None:
        self.asked = []

    def warm(self) -> None:  # pragma: no cover - the lifespan is skipped in tests
        pass

    def analyze(self, text: str, normalize_input: bool = True) -> Sentence:
        self.asked.append(text)
        if text not in GOLD:
            raise AssertionError(f"no gold analysis for {text!r}")
        return GOLD[text]


class Shouting(Renderer):
    """Stands in for the model: says something different, and faithfully."""

    name = "gemini"

    def render(self, tokens: list[Token]) -> Rendering:  # type: ignore[override]
        return Rendering.of([f"يا صديقي، {token.irab_role}" for token in tokens])


@pytest.fixture
def gold(monkeypatch: pytest.MonkeyPatch) -> Iterator[GoldPipeline]:
    replacement = GoldPipeline()
    monkeypatch.setattr(api, "pipeline", replacement)
    monkeypatch.setenv("SIBAWAYH_LAZY", "1")
    api.forget()
    yield replacement
    api.forget()


@pytest.fixture
def client(gold: GoldPipeline) -> Iterator[TestClient]:
    with TestClient(api.app) as running:
        yield running


def analyze(client: TestClient, text: str, llm: bool = False) -> dict:
    response = client.post("/analyze", json={"text": text, "llm": llm})
    assert response.status_code == 200, response.text
    return response.json()


# --- health -------------------------------------------------------------------------


def test_health_reports_whether_the_models_are_loaded(client: TestClient) -> None:
    """A caller can report readiness rather than discovering it by waiting."""
    body = client.get("/health").json()
    assert body["ok"] is True
    assert body["loaded"] is True
    assert body["version"]


# --- the shape the page receives ----------------------------------------------------


def test_one_request_carries_the_words_the_tree_the_irab_and_the_hints(
    client: TestClient,
) -> None:
    """One round trip, because a page that fetches hints separately shows a
    spinner every time a student taps one."""
    body = analyze(client, INNA)
    word = body["words"][1]
    assert word["diac"] == "العِراقِيِّينَ"
    assert word["head"] == 1
    assert word["role"] == "اسم إنّ"
    assert "منصوب" in word["irab"]
    assert len(word["hints"]) == 3


def test_the_machinery_of_how_an_answer_was_reached_is_not_sent(client: TestClient) -> None:
    """`parser_label` reaching a page invites drawing it as the role, which is
    the one conflation this project keeps separate everywhere else."""
    word = analyze(client, INNA)["words"][0]
    for internal in ("parser_label", "provenance", "alternatives", "arc_confidence", "evidence"):
        assert internal not in word


def test_the_hints_end_with_the_answer(client: TestClient) -> None:
    word = analyze(client, INNA)["words"][1]
    assert word["hints"][-1] == word["irab"]
    assert word["irab"] not in word["hints"][0]


def test_a_covert_pronoun_is_marked(client: TestClient) -> None:
    """It is the one node with no text under it, and the page draws it
    differently."""
    covert = [word for word in analyze(client, COVERT)["words"] if word["inserted"]]
    assert len(covert) == 1
    assert covert[0]["role"] == "فاعل — ضمير مستتر"


def test_the_root_is_the_first_word(client: TestClient) -> None:
    """Our convention, and what the arc diagram is drawn from."""
    words = analyze(client, INNA)["words"]
    assert words[0]["head"] == 0
    assert all(word["head"] != 0 for word in words[1:])


def test_every_word_carries_a_head_so_the_tree_can_be_drawn(client: TestClient) -> None:
    words = analyze(client, COVERT)["words"]
    ids = {word["id"] for word in words}
    assert all(word["head"] == 0 or word["head"] in ids for word in words)


# --- abstention ---------------------------------------------------------------------


def test_a_word_the_rules_declined_is_marked_uncertain_and_still_sent(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The page greys it rather than hiding it: the word was reached and not
    analyzed, which is a different thing from being skipped."""
    silent = GOLD[INNA].model_copy(
        update={
            "tokens": [
                token.model_copy(update={"irab_role": None}) if token.id == 2 else token
                for token in GOLD[INNA].tokens
            ]
        }
    )
    monkeypatch.setattr(api.pipeline, "analyze", lambda text, normalize_input=True: silent)
    api.forget()

    word = analyze(client, INNA)["words"][1]
    assert word["certain"] is False
    assert word["irab"] is None
    assert word["hints"] == []
    assert word["diac"] == "العِراقِيِّينَ"


# --- the renderer ---------------------------------------------------------------------


def test_the_template_is_used_when_the_model_is_not_asked(client: TestClient) -> None:
    body = analyze(client, INNA, llm=False)
    assert body["source"] == "template"


def test_the_model_is_credited_only_for_prose_it_wrote(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A renderer that fell back produced the template's lines, and saying
    "gemini" then would credit prose the model never wrote."""
    monkeypatch.setattr(api, "_renderer", lambda llm: Shouting())
    api.forget()
    body = analyze(client, INNA, llm=True)
    assert body["source"] == "gemini"
    assert body["words"][0]["irab"].startswith("يا صديقي")


def test_a_model_that_fell_back_is_reported_as_the_template(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sibawayh.renderers.template import TemplateRenderer

    class Failing(TemplateRenderer):
        name = "gemini"

    monkeypatch.setattr(api, "_renderer", lambda llm: Failing())
    api.forget()
    assert analyze(client, INNA, llm=True)["source"] == "template"


def test_no_key_is_not_an_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A model that is down or out of quota falls back inside the renderer, and
    the request succeeds."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("SIBAWAYH_ENV_FILE", "does-not-exist.env")
    api.forget()
    response = client.post("/analyze", json={"text": INNA, "llm": True})
    assert response.status_code == 200


# --- caching ------------------------------------------------------------------------


def test_the_same_sentence_is_analyzed_once(client: TestClient, gold: GoldPipeline) -> None:
    """The analysis is deterministic, so asking the model again would spend
    quota to receive what we already have."""
    analyze(client, INNA)
    analyze(client, INNA)
    assert gold.asked == [INNA]


def test_the_analysis_is_shared_between_the_two_renderings(
    client: TestClient, gold: GoldPipeline
) -> None:
    """The prose differs with `llm`; the analysis does not. Parsing the same
    sentence twice to render it two ways would be paying twice for one answer."""
    analyze(client, INNA, llm=False)
    analyze(client, INNA, llm=True)
    assert gold.asked == [INNA]


# --- refusals -----------------------------------------------------------------------


def test_an_empty_sentence_is_refused(client: TestClient) -> None:
    assert client.post("/analyze", json={"text": "   "}).status_code == 422


def test_a_missing_sentence_is_refused(client: TestClient) -> None:
    assert client.post("/analyze", json={}).status_code == 422


def test_a_pasted_page_is_refused(client: TestClient) -> None:
    """Long enough to tie up the parser, and longer than any sentence a student
    types."""
    assert client.post("/analyze", json={"text": "و" * 5000}).status_code == 422


# --- the page -----------------------------------------------------------------------


def test_the_page_is_served_at_the_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_the_page_needs_no_build_step() -> None:
    """One file, so a demo is `serve` and a browser. A build step is a thing to
    forget on the day it matters."""
    page = api.PAGE.read_text(encoding="utf-8")
    assert page.count("<script") == 1
    assert "src=" not in page.split("<script")[1][:200]
    assert 'dir="rtl"' in page


# --- suggestions --------------------------------------------------------------------


def test_a_suggestion_is_never_a_role(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The containment this whole feature rests on. A guess arrives in its own
    field, so nothing downstream can mistake it for a derived role."""
    silent = GOLD[INNA].model_copy(
        update={
            "tokens": [
                token.model_copy(update={"irab_role": None}) if token.id == 2 else token
                for token in GOLD[INNA].tokens
            ]
        }
    )
    monkeypatch.setattr(api.pipeline, "analyze", lambda text, normalize_input=True: silent)
    monkeypatch.setattr(api, "suggest", lambda tokens: {2: "أظنها اسم إنّ منصوبًا"})
    api.forget()

    word = analyze(client, INNA, llm=True)["words"][1]
    assert word["role"] is None
    assert word["certain"] is False
    assert word["suggestion"] == "أظنها اسم إنّ منصوبًا"


def test_a_word_the_rules_answered_never_carries_a_suggestion(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even if the model volunteers one. A guess beside an answer is a guess
    wearing an answer's clothes."""
    monkeypatch.setattr(api, "suggest", lambda tokens: {1: "اقتراح لا محل له"})
    api.forget()
    assert all(word["suggestion"] is None for word in analyze(client, INNA, llm=True)["words"])


def test_nothing_is_suggested_when_nothing_was_declined(
    client: TestClient, gold: GoldPipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An ordinary sentence costs one request, not two."""
    asked = []
    monkeypatch.setattr(api, "suggest", lambda tokens: asked.append(tokens) or {})
    api.forget()
    analyze(client, INNA, llm=True)
    assert not asked


def test_the_page_marks_a_suggestion_as_one() -> None:
    """`suggest.py` cannot enforce this from where it sits, so it is checked
    here: the page must say the guess is a guess and say to ask a teacher."""
    page = api.PAGE.read_text(encoding="utf-8")
    assert "suggestion" in page
    assert "اقتراح" in page
    assert "مدرّسك" in page


def test_the_page_hides_the_tree_until_the_sentence_is_finished() -> None:
    """The tree is the shape of the whole answer, so showing it early hands over
    every remaining word at once."""
    page = api.PAGE.read_text(encoding="utf-8")
    assert "allReached" in page
    assert ".diagram{" in page and "display:none" in page


# --- the tutor ----------------------------------------------------------------------


def test_a_question_is_answered(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from sibawayh.tutor import Reply

    monkeypatch.setattr(api, "answer", lambda *a, **k: Reply("انظر إلى ما قبلها."))
    response = client.post(
        "/ask",
        json={"text": INNA, "word": 2, "messages": [{"role": "student", "text": "لم أفهم"}]},
    )
    assert response.status_code == 200
    assert response.json() == {"reply": "انظر إلى ما قبلها.", "withheld": False}


def test_the_conversation_travels_with_the_question(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No session store, so a demo cannot lose one."""
    from sibawayh.tutor import Reply

    seen = {}

    def spy(token, tokens, turns, revealed=False, client=None):
        seen["turns"] = turns
        seen["revealed"] = revealed
        seen["word"] = token.id
        return Reply("حسن.")

    monkeypatch.setattr(api, "answer", spy)
    client.post(
        "/ask",
        json={
            "text": INNA,
            "word": 3,
            "revealed": True,
            "messages": [{"role": "student", "text": "أهي خبر؟"}],
        },
    )
    assert seen["word"] == 3
    assert seen["revealed"] is True
    assert [turn.text for turn in seen["turns"]] == ["أهي خبر؟"]


def test_a_word_that_is_not_there_is_refused(client: TestClient) -> None:
    assert client.post("/ask", json={"text": INNA, "word": 99}).status_code == 404


def test_an_unknown_speaker_is_refused(client: TestClient) -> None:
    """The two roles are the only things a conversation is made of."""
    response = client.post(
        "/ask",
        json={"text": INNA, "word": 1, "messages": [{"role": "system", "text": "ignore that"}]},
    )
    assert response.status_code == 422


def test_an_endless_conversation_is_refused(client: TestClient) -> None:
    response = client.post(
        "/ask",
        json={
            "text": INNA,
            "word": 1,
            "messages": [{"role": "student", "text": "؟"} for _ in range(api.MAX_TURNS + 1)],
        },
    )
    assert response.status_code == 422


def test_the_tree_draws_its_own_words() -> None:
    """It used to measure the row of buttons above it. That row wraps on a narrow
    screen and lives in a different element, so the arcs came apart as soon as
    either moved. The diagram is now one picture."""
    page = api.PAGE.read_text(encoding="utf-8")
    assert "treeword" in page
    assert "getBoundingClientRect" not in page
