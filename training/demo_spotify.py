"""Visible demo: the model finds Spotify's search box, searches for an artist, and opens their profile.

    python demo_spotify.py                 # searches for "Yaw Craft"
    python demo_spotify.py "Black Sherif"
"""
import sys
import time

from selenium.webdriver.common.keys import Keys

from collect import CANDIDATES_JS, make_driver, wait_until_settled
from features import element_to_text
from onnx_scorer import Scorer
from try_model import HIGHLIGHT_JS

PAUSE = 2.5  # seconds to leave each red outline on screen before acting


def pick(scorer, driver, query):
    """Rank the page's elements for `query`, outline the best one in red, and return it."""
    wait_until_settled(driver)
    ranked = scorer.rank(query, driver.execute_script(CANDIDATES_JS))[:3]
    print(f"\n{query!r}")
    for score, c in ranked:
        print(f"  {score:.3f}  {element_to_text(c)[:110]}")
    best = ranked[0][1]
    driver.execute_script(HIGHLIGHT_JS, best["id"])
    time.sleep(PAUSE)
    return driver.find_element("css selector", f'[data-selenia-id="{best["id"]}"]')


def main():
    artist = sys.argv[1] if len(sys.argv) > 1 else "Yaw Craft"
    scorer = Scorer("models/selenia-ce")
    driver = make_driver(headless=False)
    try:
        driver.get("https://open.spotify.com/")
        box = pick(scorer, driver, "what do you want to play search field")
        box.click()
        box.send_keys(artist, Keys.ENTER)
        time.sleep(3)  # results load after the URL changes
        pick(scorer, driver, f"{artist} artist profile").click()
        wait_until_settled(driver)
        print(f"\nlanded on: {driver.title}  {driver.current_url}")
        time.sleep(20)  # leave the profile on screen
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
