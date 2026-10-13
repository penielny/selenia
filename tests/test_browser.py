"""Tests that need a real Chrome: the element extractor, and the model end to end.

They run against tests/pages/shop.html, so they need no network. They are skipped when Chrome
cannot start; the end-to-end ones are also skipped when no trained model is available
(training/models/selenia-ce, or SELENIA_MODEL_DIR).
"""
import os
import pathlib

import pytest
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException

from selenia import LocalRanker, Selenia
from selenia.features import element_to_text
from selenia.local_ranker import CANDIDATES_JS

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = (ROOT / "tests" / "pages" / "shop.html").as_uri()
MODEL_DIR = os.environ.get("SELENIA_MODEL_DIR") or str(ROOT / "training" / "models" / "selenia-ce")


@pytest.fixture(scope="module")
def driver():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1366,900")
    try:
        d = webdriver.Chrome(options=opts)
    except WebDriverException as e:
        pytest.skip(f"Chrome is not available: {str(e).splitlines()[0]}")
    yield d
    d.quit()


@pytest.fixture
def page(driver):
    driver.get(PAGE)
    return driver


class KeywordScorer:
    """Stands in for the model: the share of the description's words found in the element text."""
    def scores(self, query, texts):
        words = query.lower().split()
        return [sum(w in t.lower() for w in words) / len(words) for t in texts]


def texts(driver):
    return [element_to_text(c) for c in driver.execute_script(CANDIDATES_JS)]


def test_extractor_describes_form_fields(page):
    found = texts(page)
    assert any(t.startswith("[input] | label: Username | name: username | in: form Sign in") for t in found)
    assert any(t.startswith("[password field] | placeholder: Password | in: form Sign in") for t in found)
    assert any(t.startswith("[button] Log in | in: form Sign in") for t in found)


def test_extractor_skips_hidden_elements(page):
    joined = "\n".join(texts(page))
    assert "Hidden button" not in joined and "Invisible button" not in joined


def test_extractor_tells_repeated_buttons_apart_by_their_row(page):
    removes = [t for t in texts(page) if t.startswith("[button] Remove")]
    assert len(removes) == 2
    assert "near: Mic stand" in removes[0] and "near: Guitar" in removes[1]


def test_extractor_includes_links_short_text_and_shadow_dom(page):
    cands = page.execute_script(CANDIDATES_JS)
    by_text = {c["text"]: c for c in cands}
    assert by_text["Help centre"]["href"] == "/help"
    assert "$29.99" in by_text
    assert by_text["Shadow button"]["in_shadow"] is True
    assert by_text["Log in"]["in_shadow"] is False


def test_extractor_ids_are_unique_and_stable_on_rerun(page):
    first = [(c["id"], c["text"]) for c in page.execute_script(CANDIDATES_JS)]
    second = [(c["id"], c["text"]) for c in page.execute_script(CANDIDATES_JS)]
    assert first == second
    assert len({i for i, _ in first}) == len(first)


def test_find_returns_a_usable_web_element(page):
    selenia = Selenia(page, LocalRanker(scorer=KeywordScorer()))
    box = selenia.find("label: username")
    box.send_keys("tester")
    assert box.get_attribute("value") == "tester"


def test_find_picks_the_button_in_the_right_row(page):
    selenia = Selenia(page, LocalRanker(scorer=KeywordScorer()))
    button = selenia.find("remove guitar")
    row = button.find_element("xpath", "./ancestor::tr")
    assert "Guitar" in row.text


def test_find_reaches_inside_shadow_dom(page):
    selenia = Selenia(page, LocalRanker(scorer=KeywordScorer()))
    assert selenia.find("shadow button").text == "Shadow button"


def test_find_all_returns_both_repeated_buttons(page):
    selenia = Selenia(page, LocalRanker(scorer=KeywordScorer(), min_score=1.0))
    assert [b.text for b in selenia.find_all("[button] remove")] == ["Remove", "Remove"]


@pytest.fixture(scope="module")
def model():
    pytest.importorskip("onnxruntime")
    if not os.path.exists(os.path.join(MODEL_DIR, "tokenizer.json")):
        pytest.skip(f"no trained model at {MODEL_DIR}")
    return LocalRanker(model_dir=MODEL_DIR)


@pytest.mark.parametrize("description, attribute, expected", [
    ("the log in button", "textContent", "Log in"),
    ("username field", "name", "username"),
    ("where I type my password", "type", "password"),
    ("help centre link", "textContent", "Help centre"),
    ("remove button for the guitar", "textContent", "Remove"),
])
def test_model_finds_elements(page, model, description, attribute, expected):
    assert Selenia(page, model).find(description).get_attribute(attribute) == expected


def test_model_picks_the_guitar_row(page, model):
    button = Selenia(page, model).find("remove button for the guitar")
    assert "Guitar" in button.find_element("xpath", "./ancestor::tr").text


def test_model_refuses_a_description_that_matches_nothing(page, model):
    with pytest.raises(NoSuchElementException):
        Selenia(page, model).find("the checkout basket total in euros")


def test_model_flags_the_two_remove_buttons_as_ambiguous(page, model):
    with pytest.raises(NoSuchElementException, match="ambiguous"):
        Selenia(page, model).find("remove button")
