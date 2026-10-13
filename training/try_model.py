"""Try the trained model on a live page: type a description, see which element it picks.

    python try_model.py https://www.saucedemo.com/                      # interactive, browser visible
    python try_model.py https://www.saucedemo.com/ "the login button"   # one-off, headless

The top pick is outlined in red in the browser. Empty line or q quits.
"""
import argparse

from collect import CANDIDATES_JS, make_driver, wait_until_settled
from features import element_to_text
from onnx_scorer import Scorer

HIGHLIGHT_JS = """
document.querySelectorAll('[data-selenia-pick]').forEach(e => { e.style.outline = ''; e.removeAttribute('data-selenia-pick'); });
const el = document.querySelector('[data-selenia-id="' + arguments[0] + '"]');
if (el) { el.setAttribute('data-selenia-pick', '1'); el.style.outline = '3px solid red'; el.scrollIntoView({block: 'center'}); }
"""


def show(scorer, driver, query, top):
    cands = driver.execute_script(CANDIDATES_JS)  # re-read each time: the page may have changed
    ranked = scorer.rank(query, cands)[:top]
    for score, c in ranked:
        print(f"  {score:.3f}  {element_to_text(c)[:110]}")
    if ranked:
        driver.execute_script(HIGHLIGHT_JS, ranked[0][1]["id"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("queries", nargs="*", help="descriptions to try; omit to type them interactively")
    ap.add_argument("--model", default="models/selenia-ce")
    ap.add_argument("--top", type=int, default=3)
    args = ap.parse_args()

    scorer = Scorer(args.model)
    driver = make_driver(headless=bool(args.queries))
    try:
        driver.get(args.url)
        wait_until_settled(driver)
        for q in args.queries:
            print(q)
            show(scorer, driver, q, args.top)
        while not args.queries:
            try:
                q = input("description> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q in ("", "q"):
                break
            show(scorer, driver, q, args.top)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
