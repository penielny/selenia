# Fine-tuning Selenia's element model

This folder trains a small model that answers one question: *on this page, which element matches
this description?* It replaces the LLM call. The model is
[`cross-encoder/ms-marco-MiniLM-L-6-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2)
(22.7M parameters), fine-tuned on your pages and shipped as a ~23 MB int8 ONNX file that runs on
CPU with no PyTorch.

The model never writes XPath. Selenia lists the real elements on the page, the model scores each
one, and the best score wins. It can't invent a selector, has no input-length limit (each element is
scored separately), and gives the same answer every time.

## Files

| File | What it does |
|---|---|
| `candidates.js` | Runs in the browser. Lists visible elements (including open shadow DOM) and tags each with `data-selenia-id`. |
| `features.py` | Turns an element into the text the model reads. **Training and runtime must share it.** |
| `collect.py` | Step 1. Saves page snapshots, from URLs or from inside your own Selenium tests. |
| `urls.txt` | Step 1. Starter list of ~140 pages from 30 sites. Add your own. |
| `collect_flows.py` | Step 1. Snapshots pages behind demo logins and clicks. |
| `label.py` | Step 2. Write real descriptions and pick the matching element. |
| `make_dataset.py` | Step 3. Adds synthetic descriptions, splits train/eval by page. |
| `train.py` | Step 4. Fine-tunes, evaluates before/after, exports int8 ONNX. |
| `onnx_scorer.py` | Step 5. Torch-free scorer that Selenia ships. |

## Steps

### 0. Install

```bash
pip install -r requirements-train.txt
```

### 1. Collect pages (aim for 100+ pages from at least 10 different sites/apps)

`urls.txt` already lists about 140 pages from 30 sites (automation practice sites, single-page
apps, and some real-world sites). Add your own apps at the bottom, then:

```bash
python collect.py --urls urls.txt --out data/pages.jsonl
python collect_flows.py --out data/pages.jsonl     # pages behind demo logins and clicks
```

Re-running is safe: URLs already in `pages.jsonl` are skipped. `collect_flows.py` logs into
SauceDemo, OrangeHRM and other demo apps with their published credentials and snapshots the screens
inside. Copy one of its flows as a template for your own app.

Pages behind a login, or deep inside a single-page app: call `snapshot()` from your existing tests
at each screen you care about. This is where the most valuable data comes from.

```python
from collect import snapshot
login(driver)
driver.find_element(...).click()
snapshot(driver, "data/pages.jsonl", page_id="billing-settings")
```

Each snapshot also saves a screenshot to `data/screenshots/` for labelling.

### 2. Label real descriptions (aim for 300+, written the way your testers talk)

```bash
python label.py --pages data/pages.jsonl --labels data/labels.jsonl
```

Type a description ("remove the mic stand row"), pick the element id from the shortlist.
Vary the phrasing: synonyms, product names next to repeated buttons, positions, "the X in the Y".
**These labels are the real signal.** Synthetic data teaches the format; labels teach the meaning.

### 3. Build the dataset

```bash
python make_dataset.py --pages data/pages.jsonl --labels data/labels.jsonl --out data/
```

About 20% of **sites** are held out, so the score reflects websites the model never saw (pages from
one site share layouts, so holding out single pages would overstate accuracy). It prints which sites
are held out and writes their page ids to `data/eval_pages.txt`. Evaluation uses only your manual
labels on those pages, so label them:

```bash
python label.py --pages-list data/eval_pages.txt
```

Choose the held-out sites yourself with `--eval-sites demoqa.com saucedemo.com`, or use
`--split-by page` if you only have one or two sites.

### 4. Train (Colab T4 recommended; CPU works but is slow)

```bash
python train.py --data data/ --out models/selenia-ce
```

It prints accuracy **before** (the off-the-shelf model) and **after** fine-tuning, then the int8 ONNX
score, which is the number that matters because it's what ships. Results go to
`models/selenia-ce/metrics.json`.

* `acc@1`: how often the right element is the top pick. This is the headline number.
* `acc@3`: how often it's in the top 3 (headroom for a fallback).
* `mrr`: average of 1/rank; higher is better.

Useful flags: `--epochs` (default 2), `--lr` (2e-5), `--hard-negatives` (5),
`--export-only` (re-export without retraining).

**On Colab:** upload this folder and your `data/` folder, then run
`!pip install -r requirements-train.txt` and `!python train.py --data data/ --out models/selenia-ce`.
Set Runtime → Change runtime type → T4 GPU first. Download `models/selenia-ce` when done.

### 5. Use it (no PyTorch needed)

```bash
pip install -r requirements-runtime.txt
```

```python
from onnx_scorer import Scorer
from collect import CANDIDATES_JS

scorer = Scorer("models/selenia-ce")     # picks the avx2 or arm64 int8 file for this CPU
cands = driver.execute_script(CANDIDATES_JS)
(best_score, best), (second_score, _) = scorer.rank("the sign in button", cands)[:2]
if best_score < 0.5:
    raise LookupError("no confident match")
if best_score - second_score < 0.05:
    raise LookupError("ambiguous: two elements match")
element = driver.find_element("css selector", f'[data-selenia-id="{best["id"]}"]')
```

Tune the two thresholds on your eval set. Elements inside shadow DOM can't be reached with a CSS
selector from the document; fetch those with JavaScript instead.

### 6. Improve

* Look at the eval misses, label more examples like them, retrain.
* Keep a log of real Selenia picks that testers corrected, and add them as labels.
* If `acc@1` stays low but `acc@3` is high, the model is close: add hard examples of the confusing
  pairs, or consider the larger `deberta-v3-base` / `ModernBERT-base` base models (`--base`).

## Notes

* If you change `features.py` or `candidates.js`, bump `FORMAT_VERSION` and retrain.
* iframes are not traversed yet; switch into the frame first, then collect/score.
* Do not install `optimum`: its ONNX exporter currently needs Transformers 4 and would downgrade it.
  `train.py` exports with PyTorch's own exporter and onnxruntime's quantizer instead.
