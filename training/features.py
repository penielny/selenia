"""Turns an extracted element (from candidates.js) into the short text the model reads.

Training and runtime MUST use this exact function. If you change the format,
retrain the model, or it will see text it was never trained on.
"""

FORMAT_VERSION = 1

_INPUT_NOUNS = {
    "search": "search box", "email": "email field", "password": "password field",
    "tel": "phone field", "number": "number field", "url": "url field", "date": "date picker",
    "checkbox": "checkbox", "radio": "radio button", "file": "file upload",
    "submit": "button", "button": "button", "reset": "button", "range": "slider",
}
_ROLE_NOUNS = {
    "button": "button", "link": "link", "tab": "tab", "menuitem": "menu item",
    "checkbox": "checkbox", "switch": "toggle", "combobox": "dropdown", "textbox": "input",
    "searchbox": "search box", "dialog": "dialog", "heading": "heading", "option": "option",
}


def noun(el: dict) -> str:
    """Plain-English name for the element kind, e.g. 'button', 'email field'."""
    tag, typ, role = el.get("tag", ""), (el.get("type") or "").lower(), (el.get("role") or "").lower()
    if role in _ROLE_NOUNS:
        return _ROLE_NOUNS[role]
    if tag == "input":
        return _INPUT_NOUNS.get(typ, "input")
    return {
        "button": "button", "a": "link", "select": "dropdown", "textarea": "text area",
        "img": "image", "label": "label", "summary": "toggle",
        "h1": "heading", "h2": "heading", "h3": "heading", "h4": "heading", "h5": "heading", "h6": "heading",
    }.get(tag, "text")


def position(el: dict) -> str:
    x, y = el.get("x", 0.5), el.get("y", 0.5)
    v = "top" if y < 0.2 else "bottom" if y > 0.8 else "middle"
    h = "left" if x < 0.33 else "right" if x > 0.66 else "center"
    return f"{v} {h}"


def element_to_text(el: dict) -> str:
    """e.g. '[email field] | label: Email address | placeholder: you@example.com | in: form Sign in | pos: middle center'"""
    head = noun(el)
    parts = [f"[{head}] {el.get('text', '')}".strip()]
    for key in ("label", "aria", "placeholder", "alt", "title", "name", "testid", "href"):
        val = el.get(key)
        if val and val != el.get("text"):
            parts.append(f"{key}: {val}")
    if el.get("near"):
        parts.append(f"near: {el['near']}")
    if el.get("context"):
        parts.append(f"in: {el['context']}")
    parts.append(f"pos: {position(el)}")
    return " | ".join(parts)


def cue(el: dict) -> str:
    """The most human-visible words on the element (used to write synthetic descriptions)."""
    for key in ("text", "label", "aria", "placeholder", "alt", "title"):
        val = (el.get(key) or "").strip()
        if val:
            words = val.split()
            return " ".join(words[:6])
    name = (el.get("name") or el.get("testid") or "").replace("_", " ").replace("-", " ").strip()
    return name
