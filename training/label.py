"""Step 2: write real descriptions for elements, the way testers would phrase them.

    python label.py --pages data/pages.jsonl --labels data/labels.jsonl

For each page: open its screenshot (data/screenshots/<page_id>.png), type a description
such as "the blue checkout button", then pick the matching element from the shortlist.
Commands at the description prompt:  Enter = next page,  q = quit
Commands at the pick prompt:  <id> = choose,  /words = search again,  Enter = skip
"""
import argparse
import json
import os

from rapidfuzz import fuzz

from features import element_to_text


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):  # Ctrl+D / Ctrl+C: labels are already saved
        print()
        return "q"


def shortlist(query, cands, k=12):
    scored = [(fuzz.WRatio(query.lower(), element_to_text(c).lower()), c) for c in cands]
    return [c for _, c in sorted(scored, key=lambda t: -t[0])[:k]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", default="data/pages.jsonl")
    ap.add_argument("--labels", default="data/labels.jsonl")
    ap.add_argument("--page", help="only label this page_id")
    ap.add_argument("--pages-list", help="only label page_ids listed in this file, e.g. data/eval_pages.txt")
    args = ap.parse_args()
    wanted = None
    if args.pages_list:
        with open(args.pages_list, encoding="utf-8") as f:
            wanted = {l.strip() for l in f if l.strip()}

    pages = load_jsonl(args.pages)
    done = {}
    for l in load_jsonl(args.labels):
        done[l["page_id"]] = done.get(l["page_id"], 0) + 1

    for page in pages:
        if args.page and page["page_id"] != args.page:
            continue
        if wanted is not None and page["page_id"] not in wanted:
            continue
        cands = {c["id"]: c for c in page["candidates"]}
        print(f"\n=== {page['page_id']}  {page['title']!r}  {page['url']}")
        print(f"    {len(cands)} elements, {done.get(page['page_id'], 0)} labels so far")
        while True:
            q = ask("description> ")
            if q == "q":
                return
            if not q:
                break
            search = q
            while True:
                for c in shortlist(search, cands.values()):
                    print(f"  {c['id']:5d}  {element_to_text(c)[:110]}")
                pick = ask("id> ")
                if pick == "q":
                    return
                if pick.startswith("/"):
                    search = pick[1:]
                    continue
                if pick.isdigit() and int(pick) in cands:
                    with open(args.labels, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"page_id": page["page_id"], "query": q, "gold": int(pick),
                                            "source": "manual"}) + "\n")
                    print("  saved")
                break


if __name__ == "__main__":
    main()
