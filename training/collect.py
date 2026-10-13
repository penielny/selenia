"""Step 1: save snapshots of pages (their candidate elements) for training.

Two ways to use it:

  A) From the command line, for public pages or local HTML files:
       python collect.py --urls urls.txt --out data/pages.jsonl

  B) From inside your own Selenium tests, for pages behind a login or deep in an SPA:
       from collect import snapshot
       ... log in, click around ...
       snapshot(driver, "data/pages.jsonl", page_id="checkout-step-2")

Each line of pages.jsonl is one page: {"page_id", "url", "title", "candidates": [...]}
Screenshots are saved next to it so you can see the page while labelling.
"""
import argparse
import hashlib
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "candidates.js"), encoding="utf-8") as f:
    CANDIDATES_JS = f.read()


def wait_until_settled(driver, timeout=15, quiet_ms=800):
    """Wait for document.readyState and for the DOM to stop changing (SPAs keep rendering after load)."""
    end = time.time() + timeout
    while time.time() < end and driver.execute_script("return document.readyState") != "complete":
        time.sleep(0.2)
    last, stable_since = None, time.time()
    while time.time() < end:
        size = driver.execute_script("return document.getElementsByTagName('*').length")
        if size != last:
            last, stable_since = size, time.time()
        elif (time.time() - stable_since) * 1000 >= quiet_ms:
            return
        time.sleep(0.1)


def snapshot(driver, out_path, page_id=None, screenshot=True, settle=True):
    """Extract candidates from the current page and append them to out_path. Returns the record."""
    if settle:
        wait_until_settled(driver)
    cands = driver.execute_script(CANDIDATES_JS)
    url = driver.current_url
    if page_id is None:
        page_id = hashlib.sha1(f"{url}|{len(cands)}|{time.time()}".encode()).hexdigest()[:12]
    rec = {"page_id": page_id, "url": url, "title": driver.title, "candidates": cands}
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if screenshot:
        shot_dir = os.path.join(os.path.dirname(os.path.abspath(out_path)), "screenshots")
        os.makedirs(shot_dir, exist_ok=True)
        driver.save_screenshot(os.path.join(shot_dir, f"{page_id}.png"))
    return rec


def make_driver(headless=True, chrome_binary=None):
    from selenium import webdriver
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1366,900")
    if chrome_binary:
        opts.binary_location = chrome_binary
    return webdriver.Chrome(options=opts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--urls", required=True, help="text file, one URL (or file:///path.html) per line")
    ap.add_argument("--out", default="data/pages.jsonl")
    ap.add_argument("--no-headless", action="store_true")
    ap.add_argument("--chrome-binary", default=os.environ.get("CHROME_BINARY"))
    args = ap.parse_args()

    with open(args.urls, encoding="utf-8") as f:
        urls = [u.strip() for u in f if u.strip() and not u.startswith("#")]
    driver = make_driver(headless=not args.no_headless, chrome_binary=args.chrome_binary)
    try:
        for url in urls:
            try:
                driver.get(url)
                rec = snapshot(driver, args.out)
                print(f"{rec['page_id']}  {len(rec['candidates']):5d} elements  {url}")
            except Exception as e:  # keep going; one broken page shouldn't stop the crawl
                print(f"FAILED {url}: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
