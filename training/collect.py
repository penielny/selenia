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


def existing_ids(out_path):
    if not os.path.exists(out_path):
        return set()
    with open(out_path, encoding="utf-8") as f:
        return {json.loads(l)["page_id"] for l in f if l.strip()}


def url_page_id(url):
    """Stable id for a URL, so re-running the collector recognises pages it already has."""
    return hashlib.sha1(url.strip().encode()).hexdigest()[:12]


# Titles of pages that load "successfully" but are not the page we asked for.
BLOCKED_TITLES = {
    "Privacy error": "certificate error",
    "Just a moment...": "Cloudflare bot check",
    "Attention Required! | Cloudflare": "Cloudflare bot check",
    "Access Denied": "access denied",
}


def blocked_reason(driver):
    """Why the current page is a browser error or bot wall rather than real content, or None."""
    if driver.current_url.startswith("chrome-error://"):
        return "browser error page"
    if not driver.execute_script("return document.body ? document.body.children.length : 0"):
        return "blank page"
    return BLOCKED_TITLES.get(driver.title.strip())


def snapshot(driver, out_path, page_id=None, screenshot=True, settle=True):
    """Extract candidates from the current page and append them to out_path. Returns the record.

    Re-using a page_id that is already in out_path gets a suffix (-2, -3, ...) instead of a clash.
    """
    if settle:
        wait_until_settled(driver)
    cands = driver.execute_script(CANDIDATES_JS)
    url = driver.current_url
    if page_id is None:
        page_id = url_page_id(url)
    taken = existing_ids(out_path)
    base, n = page_id, 2
    while page_id in taken:
        page_id, n = f"{base}-{n}", n + 1
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
    # Chrome silently upgrades http:// to https://; on a site with a bad certificate that leaves a blank page.
    opts.add_argument("--disable-features=HttpsUpgrades,HttpsFirstBalancedModeAutoEnable")
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
    done = existing_ids(args.out)
    todo = [u for u in urls if url_page_id(u) not in done]
    if len(todo) < len(urls):
        print(f"skipping {len(urls) - len(todo)} URLs already in {args.out}")
    driver = make_driver(headless=not args.no_headless, chrome_binary=args.chrome_binary)
    try:
        for url in todo:
            try:
                driver.get(url)
                wait_until_settled(driver)
                reason = blocked_reason(driver)
                if reason:
                    print(f"SKIPPED {url}: {reason}")
                    continue
                rec = snapshot(driver, args.out, page_id=url_page_id(url), settle=False)
                print(f"{rec['page_id']}  {len(rec['candidates']):5d} elements  {url}")
            except Exception as e:  # keep going; one broken page shouldn't stop the crawl
                msg = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
                print(f"FAILED {url}: {msg}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
