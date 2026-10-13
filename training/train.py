"""Step 4: fine-tune cross-encoder/ms-marco-MiniLM-L-6-v2, evaluate before/after, export int8 ONNX.

    python train.py --data data/ --out models/selenia-ce

Run it on a GPU (free Colab T4 is plenty); it also works on CPU, just slower.
Output folder:
    models/selenia-ce/                     fine-tuned model (PyTorch, for further training)
    models/selenia-ce/onnx/model_quint8_avx2.onnx    ~23 MB, ship this for x86 servers / CI runners
    models/selenia-ce/onnx/model_qint8_arm64.onnx    ~23 MB, ship this for ARM servers
    models/selenia-ce/metrics.json         before/after scores
"""
import argparse
import json
import os
import random
import time

from rapidfuzz import fuzz, process

from features import FORMAT_VERSION, element_to_text

BASE_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_pages(path):
    """page_id -> {element_id: element_text}"""
    return {p["page_id"]: {c["id"]: element_to_text(c) for c in p["candidates"]} for p in load_jsonl(path)}


def build_pairs(queries, pages, n_hard, n_random, rng):
    """One positive + hard negatives (look-alikes on the same page) + random negatives per query."""
    q_col, e_col, y_col = [], [], []
    for q in queries:
        page = pages[q["page_id"]]
        gold = page.get(q["gold"])
        if gold is None:
            continue
        others = {i: t for i, t in page.items() if i != q["gold"]}
        hard = [i for _, _, i in process.extract(q["query"], others, scorer=fuzz.WRatio, limit=n_hard)]
        rest = [i for i in others if i not in hard]
        negs = hard + rng.sample(rest, min(n_random, len(rest)))
        q_col.append(q["query"]); e_col.append(gold); y_col.append(1.0)
        for i in negs:
            q_col.append(q["query"]); e_col.append(others[i]); y_col.append(0.0)
    return q_col, e_col, y_col


def evaluate(model, queries, pages, label):
    """Score EVERY element on the page (hardest setting) and check where the right one ranks."""
    hits1 = hits3 = 0
    rr = 0.0
    margins = []
    t0 = time.time()
    for q in queries:
        page = pages[q["page_id"]]
        ids = list(page)
        scores = model.predict([(q["query"], page[i]) for i in ids], batch_size=256, show_progress_bar=False)
        order = sorted(range(len(ids)), key=lambda k: -scores[k])
        rank = next(r for r, k in enumerate(order) if ids[k] == q["gold"]) + 1
        hits1 += rank == 1
        hits3 += rank <= 3
        rr += 1 / rank
        if len(order) > 1:
            margins.append(float(scores[order[0]] - scores[order[1]]))
    n = max(len(queries), 1)
    res = {"acc@1": round(hits1 / n, 4), "acc@3": round(hits3 / n, 4), "mrr": round(rr / n, 4),
           "queries": len(queries), "seconds": round(time.time() - t0, 1)}
    print(f"[{label}] acc@1={res['acc@1']:.3f}  acc@3={res['acc@3']:.3f}  mrr={res['mrr']:.3f}  "
          f"({res['queries']} queries, {res['seconds']}s)")
    return res


def export_onnx(model_dir):
    """Write onnx/model.onnx plus int8 versions for x86 (avx2) and ARM.

    Uses PyTorch's own exporter and onnxruntime's quantizer, so no `optimum` package is needed
    (at the time of writing, optimum's ONNX exporter still pins Transformers 4, while
    sentence-transformers 6 needs Transformers 5).
    """
    import torch
    from onnxruntime.quantization import QuantType, quantize_dynamic
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    onnx_dir = os.path.join(model_dir, "onnx")
    os.makedirs(onnx_dir, exist_ok=True)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir).eval()
    tok = AutoTokenizer.from_pretrained(model_dir)
    enc = tok([("the sign in button", "[button] Sign in | in: form Login | pos: middle center")],
              return_tensors="pt")
    names = [k for k in ("input_ids", "attention_mask", "token_type_ids") if k in enc]

    class Wrapper(torch.nn.Module):  # named tensor inputs -> logits only
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, input_ids, attention_mask, token_type_ids=None):
            kw = {"input_ids": input_ids, "attention_mask": attention_mask}
            if token_type_ids is not None:  # BERT/MiniLM use it; ModernBERT/DeBERTa-style may not
                kw["token_type_ids"] = token_type_ids
            return self.m(**kw).logits

    full = os.path.join(onnx_dir, "model.onnx")
    batch, seq = torch.export.Dim("batch"), torch.export.Dim("seq")
    torch.onnx.export(Wrapper(model), tuple(enc[k] for k in names), full,
                      input_names=names, output_names=["logits"],
                      dynamic_shapes=tuple({0: batch, 1: seq} for _ in names),
                      dynamo=True, external_data=False)
    # The new exporter writes intermediate shape annotations that trip onnxruntime's quantizer
    # ("Inferred shape and existing shape differ"). They're optional, so drop them first.
    import onnx
    graph = onnx.load(full)
    del graph.graph.value_info[:]
    onnx.save(graph, full)
    quantize_dynamic(full, os.path.join(onnx_dir, "model_quint8_avx2.onnx"), weight_type=QuantType.QUInt8)
    quantize_dynamic(full, os.path.join(onnx_dir, "model_qint8_arm64.onnx"), weight_type=QuantType.QInt8)
    for f in sorted(os.listdir(onnx_dir)):
        print(f"  onnx/{f}  {os.path.getsize(os.path.join(onnx_dir, f)) / 1e6:.1f} MB")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="data/")
    ap.add_argument("--out", default="models/selenia-ce")
    ap.add_argument("--base", default=BASE_MODEL)
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--hard-negatives", type=int, default=5)
    ap.add_argument("--random-negatives", type=int, default=3)
    ap.add_argument("--max-length", type=int, default=128, help="tokens per (query, element) pair")
    ap.add_argument("--eval-limit", type=int, default=500, help="cap eval queries to keep it quick")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--export-only", action="store_true", help="skip training; export an already-trained --out")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    import torch
    from datasets import Dataset
    from sentence_transformers.cross_encoder import (CrossEncoder, CrossEncoderTrainer,
                                                     CrossEncoderTrainingArguments)
    from sentence_transformers.cross_encoder.losses import BinaryCrossEntropyLoss

    rng = random.Random(args.seed)
    pages = load_pages(os.path.join(args.data, "pages.jsonl"))
    train_q = load_jsonl(os.path.join(args.data, "train_queries.jsonl"))
    eval_q = load_jsonl(os.path.join(args.data, "eval_queries.jsonl"))
    rng.shuffle(eval_q)
    eval_q = eval_q[: args.eval_limit]
    metrics_path = os.path.join(args.out, "metrics.json")

    if args.export_only:
        print("exporting ONNX ...")
        export_onnx(args.out)
        check_int8(args.out, eval_q, pages, metrics_path)
        return

    model = CrossEncoder(args.base, num_labels=1, max_length=args.max_length)
    before = evaluate(model, eval_q, pages, "before fine-tuning") if eval_q else {}

    q, e, y = build_pairs(train_q, pages, args.hard_negatives, args.random_negatives, rng)
    train_ds = Dataset.from_dict({"query": q, "element": e, "label": y}).shuffle(seed=args.seed)
    neg_per_pos = args.hard_negatives + args.random_negatives
    print(f"training pairs: {len(train_ds)} ({sum(y):.0f} positive)")

    loss = BinaryCrossEntropyLoss(model, pos_weight=torch.tensor(float(neg_per_pos)))
    targs = CrossEncoderTrainingArguments(
        output_dir=os.path.join(args.out, "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        learning_rate=args.lr,
        warmup_ratio=0.1,
        fp16=torch.cuda.is_available(),
        logging_steps=50,
        save_strategy="no",
        report_to="none",
        seed=args.seed,
    )
    CrossEncoderTrainer(model=model, args=targs, train_dataset=train_ds, loss=loss).train()
    model.save_pretrained(args.out)

    after = evaluate(model, eval_q, pages, "after fine-tuning") if eval_q else {}
    metrics = {"base": args.base, "feature_format": FORMAT_VERSION, "before": before, "after": after,
               "train_queries": len(train_q), "train_pairs": len(train_ds)}

    with open(metrics_path, "w") as f:  # saved before export, so a failed export loses nothing
        json.dump(metrics, f, indent=2)
    print(f"saved to {args.out}")

    if not args.no_export:
        print("exporting ONNX ...")
        export_onnx(args.out)
        check_int8(args.out, eval_q, pages, metrics_path)


class _OnnxAdapter:
    """Lets evaluate() run on the torch-free scorer, so we test exactly what ships."""
    def __init__(self, model_dir):
        from onnx_scorer import Scorer
        self.s = Scorer(model_dir)

    def predict(self, pairs, **_):
        return self.s.scores(pairs[0][0], [t for _, t in pairs]) if pairs else []


def check_int8(model_dir, eval_q, pages, metrics_path):
    if not eval_q:
        return
    res = evaluate(_OnnxAdapter(model_dir), eval_q, pages, "after, int8 ONNX (what ships)")
    metrics = json.load(open(metrics_path)) if os.path.exists(metrics_path) else {}
    metrics["after_int8"] = res
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)


if __name__ == "__main__":
    main()
