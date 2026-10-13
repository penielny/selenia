"""Downloads the published model on first use and keeps it in a local cache.

The files live as assets on a GitHub release of this repo. Only the two files this machine needs
are fetched (the tokenizer and the int8 model for this CPU, about 24 MB), each checked against a
known SHA-256 before it is used.

    SELENIA_CACHE_DIR   where to keep downloads (default ~/.cache/selenia)
    SELENIA_MODEL_URL   fetch from this base URL instead, e.g. an internal mirror

To publish a retrained model: upload the three files to a new release tag, then update MODEL_TAG
and SHA256 below.
"""
import hashlib
import os
import shutil
import sys
import tempfile
import urllib.request

MODEL_TAG = "model-v1"
DEFAULT_URL = f"https://github.com/penielny/selenia/releases/download/{MODEL_TAG}"
SHA256 = {
    "tokenizer.json": "2fc687b11de0bc1b3d8348f92e3b49ef1089a621506c7661fbf3248fcd54947e",
    "model_qint8_arm64.onnx": "9c0341f7ad0cbf51948aa382a17ff5ab90aacdc474bf412702dbd66b394cedce",
    "model_quint8_avx2.onnx": "d68e324a5bac5ae68e53b303d0b9ac7089ef12cf2d05319d2d918c46cef96500",
}


def cache_dir():
    root = os.environ.get("SELENIA_CACHE_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "selenia")
    return os.path.join(root, MODEL_TAG)


def _download(url, dest, sha256=None):
    """Fetch url to dest. Writes to a temp file first so an interrupted download leaves nothing behind."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), suffix=".part")
    try:
        digest = hashlib.sha256()
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(url, timeout=60) as resp:
            for chunk in iter(lambda: resp.read(1 << 20), b""):
                out.write(chunk)
                digest.update(chunk)
        if sha256 and digest.hexdigest() != sha256:
            raise RuntimeError(f"{url} does not match its expected checksum; refusing to use it")
        shutil.move(tmp, dest)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def ensure_model(onnx_name):
    """Return a model folder holding tokenizer.json and onnx/<onnx_name>, downloading what is missing."""
    base = os.environ.get("SELENIA_MODEL_URL")
    verify = not base  # checksums describe the published model, not a mirror's own
    base = (base or DEFAULT_URL).rstrip("/")
    folder = cache_dir()
    wanted = {"tokenizer.json": os.path.join(folder, "tokenizer.json"),
              onnx_name: os.path.join(folder, "onnx", onnx_name)}
    missing = {name: path for name, path in wanted.items() if not os.path.exists(path)}
    if missing:
        print(f"selenia: downloading model ({MODEL_TAG}) to {folder} ...", file=sys.stderr)
    for name, path in missing.items():
        try:
            _download(f"{base}/{name}", path, SHA256.get(name) if verify else None)
        except OSError as e:  # no network, 404, disk full...
            raise RuntimeError(
                f"could not download the Selenia model from {base}/{name}: {e}. "
                "Check your connection, or pass LocalRanker(model_dir=...) / set SELENIA_MODEL_DIR "
                "to a model folder you already have.") from e
    return folder
