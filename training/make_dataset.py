"""Step 3: build training and evaluation queries.

    python make_dataset.py --pages data/pages.jsonl --labels data/labels.jsonl --out data/

Writes data/train_queries.jsonl and data/eval_queries.jsonl, each line:
    {"page_id", "query", "gold", "source": "manual" | "synthetic"}

How it works:
  * Pages are split into train/eval BY PAGE, so the score you see is on pages the model never saw.
  * Synthetic queries are generated from element attributes ("the Sign in button in the login form").
    They are cheap but easy, so they mostly teach the model the format.
  * Manual labels (from label.py) are the real signal. Eval uses ONLY manual labels when you have
    any; with none, it falls back to synthetic ones and warns that the score is optimistic.
"""
import argparse
import hashlib
import json
import os
import random
from collections import Counter

from features import cue, noun, position

SYNONYMS = {
    "sign in": ["log in", "login"], "log in": ["sign in"], "login": ["sign in", "log in"],
    "sign up": ["register", "create account"], "register": ["sign up"],
    "search": ["find", "look up"], "submit": ["send", "confirm"], "cart": ["basket", "bag"],
    "menu": ["navigation menu"], "close": ["dismiss", "x"], "delete": ["remove"],
    "next": ["continue"], "continue": ["next"], "cancel": ["go back"], "email": ["e-mail"],
}

TEMPLATES = [
    "{cue} {noun}", "the {cue} {noun}", "{noun} labelled {cue}", "the {noun} that says {cue}",
    "{cue}", "the {noun} for {cue}",
]
INPUT_TEMPLATES = ["the {cue} field", "where I type my {cue}", "input for {cue}", "the {cue} box"]
CONTEXT_TEMPLATES = ["the {cue} {noun} in the {ctx}", "{cue} {noun} inside the {ctx}"]
NEAR_TEMPLATES = ["the {cue} {noun} for {near}", "{cue} {noun} next to {near}", "the {near} {cue} {noun}"]
POSITION_TEMPLATES =["the {cue} {noun} at the {pos}", "{cue} {noun} near the {pos} of the page"]
INPUT_NOUNS = {"input", "email field", "password field", "search box", "phone field", "number field",
               "url field", "text area"}


def load_jsonl(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def is_eval_page(page_id, eval_frac):
    h = int(hashlib.md5(page_id.encode()).hexdigest(), 16) % 1000
    return h < eval_frac * 1000


def vary(text, rng):
    low = text.lower()
    for k, alts in SYNONYMS.items():
        if k in low and rng.random() < 0.35:
            return low.replace(k, rng.choice(alts))
    return low if rng.random() < 0.5 else text


def synth_for_page(page, rng, per_page):
    cands = page["candidates"]
    keys = Counter((noun(c), cue(c).lower()) for c in cands)
    ctx_keys = Counter((noun(c), cue(c).lower(), c.get("context", "")) for c in cands)
    pos_keys = Counter((noun(c), cue(c).lower(), position(c)) for c in cands)
    near_keys = Counter((noun(c), cue(c).lower(), c.get("near", "")) for c in cands)
    pool = [c for c in cands if 0 < len(cue(c)) <= 60 and noun(c) != "text" or (noun(c) == "text" and 0 < len(cue(c)) <= 40)]
    rng.shuffle(pool)
    out = []
    for c in pool[:per_page]:
        n, q = noun(c), cue(c)
        ctx = (c.get("context") or "").split(" ", 1)
        ctx_text = (ctx[1] + " " + ctx[0]) if len(ctx) == 2 else ctx[0]
        options = []
        if keys[(n, q.lower())] == 1:  # unambiguous on its own
            options += TEMPLATES + (INPUT_TEMPLATES if n in INPUT_NOUNS else [])
        if ctx_text and ctx_keys[(n, q.lower(), c.get("context", ""))] == 1:
            options += CONTEXT_TEMPLATES
        if pos_keys[(n, q.lower(), position(c))] == 1:
            options += POSITION_TEMPLATES
        near = c.get("near", "")
        if near and near_keys[(n, q.lower(), near)] == 1:
            options += NEAR_TEMPLATES * 2  # weight: this is the hard, valuable case (repeated buttons)
        if not options:
            continue  # duplicates we can't tell apart: a description would be a lie
        tpl = rng.choice(options)
        query = tpl.format(cue=vary(q, rng), noun=n, ctx=ctx_text.lower(), pos=position(c), near=near)
        out.append({"page_id": page["page_id"], "query": query, "gold": c["id"], "source": "synthetic"})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", default="data/pages.jsonl")
    ap.add_argument("--labels", default="data/labels.jsonl")
    ap.add_argument("--out", default="data/")
    ap.add_argument("--eval-frac", type=float, default=0.2, help="share of pages held out for evaluation")
    ap.add_argument("--synthetic-per-page", type=int, default=40)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    pages = load_jsonl(args.pages)
    page_ids = {p["page_id"] for p in pages}
    manual = [l for l in load_jsonl(args.labels) if l["page_id"] in page_ids]
    if len(pages) < 5:
        print(f"WARNING: only {len(pages)} pages. Aim for 100+ pages from varied sites before trusting results.")

    train, evals = [], []
    for page in pages:
        held_out = is_eval_page(page["page_id"], args.eval_frac)
        synth = synth_for_page(page, rng, args.synthetic_per_page)
        man = [l for l in manual if l["page_id"] == page["page_id"]]
        (evals if held_out else train).extend(man + synth)

    if not any(e["source"] == "manual" for e in evals):
        print("WARNING: no manual labels on eval pages, so eval uses synthetic queries and will look "
              "better than real use. Label some held-out pages with label.py.")
    else:
        evals = [e for e in evals if e["source"] == "manual"]

    os.makedirs(args.out, exist_ok=True)
    for name, rows in (("train_queries.jsonl", train), ("eval_queries.jsonl", evals)):
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    src = Counter(r["source"] for r in train)
    print(f"train: {len(train)} queries ({dict(src)})  eval: {len(evals)} queries  "
          f"pages: {len(pages)} ({sum(is_eval_page(p, args.eval_frac) for p in page_ids)} held out)")


if __name__ == "__main__":
    main()
