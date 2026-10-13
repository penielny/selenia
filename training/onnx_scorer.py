"""Step 5: score elements with the exported model, using only onnxruntime + tokenizers (no PyTorch).

This is what Selenia ships for runtime. Install size is a few tens of MB instead of hundreds.

    from onnx_scorer import Scorer
    s = Scorer("models/selenia-ce")              # picks the int8 file for this CPU
    s.rank("the sign in button", candidates)     # -> [(score, element), ...] best first
"""
import os
import platform

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from features import element_to_text


def default_onnx_file(model_dir):
    arm = platform.machine().lower() in ("arm64", "aarch64")
    name = "model_qint8_arm64.onnx" if arm else "model_quint8_avx2.onnx"
    path = os.path.join(model_dir, "onnx", name)
    return path if os.path.exists(path) else os.path.join(model_dir, "onnx", "model.onnx")


class Scorer:
    def __init__(self, model_dir, onnx_file=None, max_length=128, threads=None):
        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
        self.session = ort.InferenceSession(onnx_file or default_onnx_file(model_dir), opts,
                                            providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}
        self.tok = Tokenizer.from_file(os.path.join(model_dir, "tokenizer.json"))
        self.tok.enable_truncation(max_length=max_length)
        self.tok.enable_padding()

    def scores(self, query, texts, batch=64):
        out = []
        for i in range(0, len(texts), batch):
            enc = self.tok.encode_batch([(query, t) for t in texts[i:i + batch]])
            feed = {
                "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
                "token_type_ids": np.array([e.type_ids for e in enc], dtype=np.int64),
            }
            logits = self.session.run(None, {k: v for k, v in feed.items() if k in self.inputs})[0]
            out.append(logits.reshape(-1))
        return 1 / (1 + np.exp(-np.concatenate(out))) if out else np.array([])  # 0..1 confidence

    def rank(self, query, candidates):
        s = self.scores(query, [element_to_text(c) for c in candidates])
        return sorted(zip(s.tolist(), candidates), key=lambda t: -t[0])
