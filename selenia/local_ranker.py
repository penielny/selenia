"""Find elements with the small fine-tuned ranking model.

The model never writes XPath. Selenia lists the real elements on the page, the model scores each
one against the description, and the best score wins. Runs on onnxruntime + tokenizers (no
PyTorch). The model is downloaded on first use, or pass a folder produced by training/train.py.
"""
import os
import platform

from selenium.common.exceptions import NoSuchElementException

from .features import element_to_text
from .model_store import ensure_model

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "candidates.js"), encoding="utf-8") as f:
    CANDIDATES_JS = f.read()

# Looks through open shadow roots too, which a CSS selector from the document cannot reach.
FIND_BY_ID_JS = """
const id = String(arguments[0]);
function search(root) {
  const hit = root.querySelector('[data-selenia-id="' + id + '"]');
  if (hit) return hit;
  for (const el of root.querySelectorAll('*')) {
    if (el.shadowRoot) { const inner = search(el.shadowRoot); if (inner) return inner; }
  }
  return null;
}
return search(document);
"""


def onnx_name():
    arm = platform.machine().lower() in ("arm64", "aarch64")
    return "model_qint8_arm64.onnx" if arm else "model_quint8_avx2.onnx"


def default_onnx_file(model_dir):
    path = os.path.join(model_dir, "onnx", onnx_name())
    return path if os.path.exists(path) else os.path.join(model_dir, "onnx", "model.onnx")


class Scorer:
    """Scores (description, element text) pairs with the exported ONNX model."""

    def __init__(self, model_dir, onnx_file=None, max_length=128, threads=None):
        try:
            import numpy as np
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except ImportError as e:
            raise ImportError("LocalRanker needs onnxruntime and tokenizers: pip install onnxruntime tokenizers") from e
        onnx_file = onnx_file or default_onnx_file(model_dir)
        tokenizer_file = os.path.join(model_dir, "tokenizer.json")
        for path in (onnx_file, tokenizer_file):
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"{path} not found. model_dir must be a folder written by training/train.py "
                    "(it holds tokenizer.json and onnx/).")
        self.np = np
        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
        self.session = ort.InferenceSession(onnx_file, opts, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}
        self.tok = Tokenizer.from_file(tokenizer_file)
        self.tok.enable_truncation(max_length=max_length)
        self.tok.enable_padding()

    def scores(self, query, texts, batch=64):
        np, out = self.np, []
        for i in range(0, len(texts), batch):
            enc = self.tok.encode_batch([(query, t) for t in texts[i:i + batch]])
            feed = {
                "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
                "token_type_ids": np.array([e.type_ids for e in enc], dtype=np.int64),
            }
            logits = self.session.run(None, {k: v for k, v in feed.items() if k in self.inputs})[0]
            out.append(logits.reshape(-1))
        if not out:
            return []
        return (1 / (1 + np.exp(-np.concatenate(out)))).tolist()  # 0..1 confidence


class LocalRanker:
    """Ranks the page's real elements against a description. Selenia uses it to find elements.

    model_dir:  folder written by training/train.py. Defaults to $SELENIA_MODEL_DIR, else the
                published model, downloaded once into the cache (see model_store.py).
    min_score:  reject the best match when the model is less confident than this (0..1).
    min_margin: reject when the runner-up is this close to the best match (two elements fit).
                Set to 0 to always take the top pick.
    """

    def __init__(self, model_dir=None, min_score=0.5, min_margin=0.05, scorer=None):
        if scorer is None:
            model_dir = model_dir or os.environ.get("SELENIA_MODEL_DIR") or ensure_model(onnx_name())
            scorer = Scorer(model_dir)
        self.scorer = scorer
        self.min_score = min_score
        self.min_margin = min_margin

    def rank(self, driver, description):
        """Every candidate element on the current page as (score, element dict), best first."""
        cands = driver.execute_script(CANDIDATES_JS)
        scores = self.scorer.scores(description, [element_to_text(c) for c in cands])
        return sorted(zip(scores, cands), key=lambda t: -t[0])

    def _element(self, driver, cand):
        el = driver.execute_script(FIND_BY_ID_JS, cand["id"])
        if el is None:
            raise NoSuchElementException(f"element left the page before it could be used: {element_to_text(cand)}")
        return el

    def locate(self, driver, description):
        ranked = self.rank(driver, description)
        if not ranked or ranked[0][0] < self.min_score:
            best = f" Best guess ({ranked[0][0]:.2f}): {element_to_text(ranked[0][1])}" if ranked else ""
            raise NoSuchElementException(f"no confident match for {description!r}.{best}")
        if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < self.min_margin:
            raise NoSuchElementException(
                f"ambiguous: two elements match {description!r} "
                f"({ranked[0][0]:.2f}: {element_to_text(ranked[0][1])}  |  "
                f"{ranked[1][0]:.2f}: {element_to_text(ranked[1][1])}). Add detail to the description.")
        return self._element(driver, ranked[0][1])

    def locate_all(self, driver, description):
        return [self._element(driver, c) for score, c in self.rank(driver, description) if score >= self.min_score]
