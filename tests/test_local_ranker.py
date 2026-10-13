import os

import pytest
from selenium.common.exceptions import NoSuchElementException

from selenia import LocalRanker, Selenia

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize("name", ["features.py", "candidates.js"])
def test_runtime_matches_training(name):
    """The model only works if runtime describes elements exactly as training did."""
    with open(os.path.join(ROOT, "training", name), encoding="utf-8") as a, \
            open(os.path.join(ROOT, "selenia", name), encoding="utf-8") as b:
        assert a.read() == b.read(), f"selenia/{name} and training/{name} differ: copy one over the other"


class FakeScorer:
    def __init__(self, scores):
        self._scores = scores

    def scores(self, query, texts):
        return self._scores[:len(texts)]


class FakeDriver:
    """Returns three candidates for the extractor script and echoes the id for the lookup script."""
    def execute_script(self, script, *args):
        if args:
            return f"element-{args[0]}"
        return [{"id": i, "tag": "button", "text": t} for i, t in enumerate(["Login", "Sign up", "Help"])]


def selenia_with(scores, **kw):
    return Selenia(FakeDriver(), LocalRanker(scorer=FakeScorer(scores), **kw))


def test_find_returns_best_match():
    assert selenia_with([0.1, 0.9, 0.2]).find("sign up") == "element-1"


def test_find_rejects_low_confidence():
    with pytest.raises(NoSuchElementException, match="no confident match"):
        selenia_with([0.1, 0.4, 0.2]).find("sign up")


def test_find_rejects_ambiguous():
    with pytest.raises(NoSuchElementException, match="ambiguous"):
        selenia_with([0.92, 0.9, 0.2]).find("button")


def test_margin_zero_takes_top_pick():
    assert selenia_with([0.92, 0.9, 0.2], min_margin=0).find("button") == "element-0"


def test_find_all_returns_confident_matches_best_first():
    assert selenia_with([0.6, 0.9, 0.2]).find_all("button") == ["element-1", "element-0"]


def test_rank_orders_every_candidate_best_first():
    ranked = LocalRanker(scorer=FakeScorer([0.1, 0.9, 0.2])).rank(FakeDriver(), "anything")
    assert [(score, c["text"]) for score, c in ranked] == [(0.9, "Sign up"), (0.2, "Help"), (0.1, "Login")]


def test_scorer_reads_the_text_built_by_features():
    seen = {}

    class Recording(FakeScorer):
        def scores(self, query, texts):
            seen["query"], seen["texts"] = query, texts
            return super().scores(query, texts)

    LocalRanker(scorer=Recording([0.9, 0.1, 0.1])).rank(FakeDriver(), "the login button")
    assert seen["query"] == "the login button"
    assert seen["texts"][0] == "[button] Login | pos: middle center"


def test_single_candidate_is_never_ambiguous():
    class OneButton(FakeDriver):
        def execute_script(self, script, *args):
            return f"element-{args[0]}" if args else [{"id": 0, "tag": "button", "text": "Login"}]

    assert LocalRanker(scorer=FakeScorer([0.9])).locate(OneButton(), "login") == "element-0"


def test_empty_page_raises_instead_of_crashing():
    class Empty(FakeDriver):
        def execute_script(self, script, *args):
            return []

    ranker = LocalRanker(scorer=FakeScorer([]))
    with pytest.raises(NoSuchElementException, match="no confident match"):
        ranker.locate(Empty(), "login")
    assert ranker.locate_all(Empty(), "login") == []


def test_element_that_left_the_page_raises():
    class Vanishing(FakeDriver):
        def execute_script(self, script, *args):
            return None if args else super().execute_script(script)

    with pytest.raises(NoSuchElementException, match="left the page"):
        LocalRanker(scorer=FakeScorer([0.1, 0.9, 0.2])).locate(Vanishing(), "sign up")


def test_error_messages_name_the_candidates():
    with pytest.raises(NoSuchElementException) as low:
        selenia_with([0.1, 0.4, 0.2]).find("sign up")
    assert "[button] Sign up" in str(low.value) and "0.40" in str(low.value)
    with pytest.raises(NoSuchElementException) as tie:
        selenia_with([0.92, 0.9, 0.2]).find("button")
    assert "[button] Login" in str(tie.value) and "[button] Sign up" in str(tie.value)


def test_model_dir_wins_over_environment_and_download(monkeypatch, tmp_path):
    from selenia import local_ranker
    used = []
    monkeypatch.setattr(local_ranker, "Scorer", lambda model_dir: used.append(model_dir))
    monkeypatch.setattr(local_ranker, "ensure_model", lambda name: "downloaded")
    monkeypatch.setenv("SELENIA_MODEL_DIR", "from-env")
    LocalRanker(model_dir="explicit")
    LocalRanker()
    monkeypatch.delenv("SELENIA_MODEL_DIR")
    LocalRanker()
    assert used == ["explicit", "from-env", "downloaded"]


def test_scorer_explains_a_folder_without_a_model(tmp_path):
    pytest.importorskip("onnxruntime")
    from selenia.local_ranker import Scorer
    with pytest.raises(FileNotFoundError, match="train.py"):
        Scorer(str(tmp_path))


def test_onnx_file_falls_back_to_unquantized(tmp_path):
    from selenia.local_ranker import default_onnx_file, onnx_name
    (tmp_path / "onnx").mkdir()
    assert default_onnx_file(str(tmp_path)).endswith(os.path.join("onnx", "model.onnx"))
    (tmp_path / "onnx" / onnx_name()).write_bytes(b"x")
    assert default_onnx_file(str(tmp_path)).endswith(onnx_name())
