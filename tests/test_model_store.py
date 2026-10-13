import hashlib
import os

import pytest


@pytest.fixture
def store(tmp_path, monkeypatch):
    """model_store pointed at a local folder acting as the release, with an empty cache."""
    from selenia import model_store
    release = tmp_path / "release"
    release.mkdir()
    (release / "tokenizer.json").write_text("{}")
    (release / "m.onnx").write_bytes(b"weights")
    monkeypatch.setenv("SELENIA_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("SELENIA_MODEL_URL", raising=False)
    monkeypatch.setattr(model_store, "DEFAULT_URL", release.as_uri())
    return model_store, release


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_model_downloads_once_then_uses_cache(store, monkeypatch):
    model_store, release = store
    monkeypatch.setattr(model_store, "SHA256", {n: sha(release / n) for n in ("tokenizer.json", "m.onnx")})
    folder = model_store.ensure_model("m.onnx")
    assert open(os.path.join(folder, "onnx", "m.onnx"), "rb").read() == b"weights"
    assert os.path.exists(os.path.join(folder, "tokenizer.json"))
    (release / "m.onnx").unlink()  # a second call must not need the release
    assert model_store.ensure_model("m.onnx") == folder


def test_model_with_wrong_checksum_is_refused(store, monkeypatch):
    model_store, release = store
    monkeypatch.setattr(model_store, "SHA256", {"tokenizer.json": sha(release / "tokenizer.json"), "m.onnx": "0" * 64})
    with pytest.raises(RuntimeError, match="checksum"):
        model_store.ensure_model("m.onnx")
    assert not os.path.exists(os.path.join(model_store.cache_dir(), "onnx", "m.onnx"))


def test_model_download_failure_explains_what_to_do(store, monkeypatch):
    model_store, release = store
    monkeypatch.setattr(model_store, "SHA256", {})
    (release / "m.onnx").unlink()
    with pytest.raises(RuntimeError, match="SELENIA_MODEL_DIR"):
        model_store.ensure_model("m.onnx")


def test_interrupted_download_leaves_no_partial_file(store, monkeypatch):
    model_store, release = store
    monkeypatch.setattr(model_store, "SHA256", {"m.onnx": "0" * 64})
    with pytest.raises(RuntimeError):
        model_store.ensure_model("m.onnx")
    leftovers = [f for _, _, files in os.walk(model_store.cache_dir()) for f in files if f.endswith(".part")]
    assert leftovers == []


def test_mirror_url_is_used_without_checksums(store, monkeypatch):
    model_store, release = store
    monkeypatch.setattr(model_store, "DEFAULT_URL", "file:///nonexistent")
    monkeypatch.setattr(model_store, "SHA256", {"tokenizer.json": "0" * 64, "m.onnx": "0" * 64})
    monkeypatch.setenv("SELENIA_MODEL_URL", release.as_uri() + "/")
    folder = model_store.ensure_model("m.onnx")
    assert os.path.exists(os.path.join(folder, "onnx", "m.onnx"))


def test_cache_is_separate_per_model_version(store, monkeypatch):
    model_store, _ = store
    first = model_store.cache_dir()
    monkeypatch.setattr(model_store, "MODEL_TAG", "model-v2")
    assert model_store.cache_dir() != first and model_store.cache_dir().endswith("model-v2")


def test_published_checksums_cover_every_platform_file():
    from selenia import model_store
    assert set(model_store.SHA256) == {"tokenizer.json", "model_qint8_arm64.onnx", "model_quint8_avx2.onnx"}
    assert all(len(h) == 64 for h in model_store.SHA256.values())
