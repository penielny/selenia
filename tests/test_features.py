import pytest

from selenia.features import cue, element_to_text, noun, position


@pytest.mark.parametrize("el, expected", [
    ({"tag": "button"}, "button"),
    ({"tag": "a"}, "link"),
    ({"tag": "select"}, "dropdown"),
    ({"tag": "textarea"}, "text area"),
    ({"tag": "img"}, "image"),
    ({"tag": "h2"}, "heading"),
    ({"tag": "input"}, "input"),
    ({"tag": "input", "type": "password"}, "password field"),
    ({"tag": "input", "type": "EMAIL"}, "email field"),
    ({"tag": "input", "type": "checkbox"}, "checkbox"),
    ({"tag": "input", "type": "submit"}, "button"),
    ({"tag": "div", "role": "button"}, "button"),
    ({"tag": "input", "type": "text", "role": "combobox"}, "dropdown"),  # role beats tag
    ({"tag": "span"}, "text"),
    ({}, "text"),
])
def test_noun(el, expected):
    assert noun(el) == expected


@pytest.mark.parametrize("x, y, expected", [
    (0.1, 0.1, "top left"), (0.5, 0.5, "middle center"), (0.9, 0.9, "bottom right"),
    (0.5, 0.1, "top center"), (0.1, 0.9, "bottom left"),
])
def test_position(x, y, expected):
    assert position({"x": x, "y": y}) == expected


def test_position_defaults_to_the_middle():
    assert position({}) == "middle center"


def test_element_text_lists_only_the_fields_that_have_values():
    el = {"tag": "input", "type": "email", "text": "", "label": "Email address", "aria": "",
          "placeholder": "you@example.com", "name": "", "context": "form Sign in", "near": "", "x": 0.5, "y": 0.5}
    assert element_to_text(el) == ("[email field] | label: Email address | placeholder: you@example.com"
                                   " | in: form Sign in | pos: middle center")


def test_element_text_does_not_repeat_the_visible_text():
    el = {"tag": "button", "text": "Save", "aria": "Save", "title": "Save changes", "x": 0.9, "y": 0.1}
    assert element_to_text(el) == "[button] Save | title: Save changes | pos: top right"


def test_element_text_includes_the_neighbouring_heading():
    el = {"tag": "button", "text": "Remove", "near": "Mic stand", "x": 0.5, "y": 0.5}
    assert element_to_text(el) == "[button] Remove | near: Mic stand | pos: middle center"


def test_cue_prefers_visible_text_and_keeps_six_words():
    assert cue({"text": "one two three four five six seven", "label": "ignored"}) == "one two three four five six"


def test_cue_falls_back_through_label_placeholder_and_name():
    assert cue({"text": "", "label": "Email"}) == "Email"
    assert cue({"placeholder": "Search"}) == "Search"
    assert cue({"name": "user_first-name"}) == "user first name"
    assert cue({"testid": "login-button"}) == "login button"
    assert cue({}) == ""
