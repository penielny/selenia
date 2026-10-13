# Selenia

Selenium wrapper that finds elements from natural language using a small local model

---

## 🚀 Overview
Selenia lets you locate web elements by describing them in plain English. A small fine-tuned model
(about 24 MB, CPU only, no PyTorch) scores the real elements on the page against your description and
returns the best one. Nothing leaves your machine, and it never invents a selector.

## ✨ Features
- 🔍 Find elements by describing them in plain English
- ⚡ Runs locally on CPU: no LLM, no server, no API key
- 🛑 Refuses to guess: raises when no element fits or when two fit equally well
- 🧪 Easy integration with Selenium WebDriver, including elements inside open shadow DOM
- 🧩 Retrain on your own pages with the kit in [training/](training/README.md)

## 📦 Installation
```bash
pip install selenia
```
Or from source:
```bash
pip install .
```

## 🛠️ Usage Example
```python
from selenium import webdriver
from selenia import Selenia

driver = webdriver.Chrome()
selenia = Selenia(driver)   # downloads the model on first use

driver.get("https://www.saucedemo.com/")
selenia.find("username field").send_keys("standard_user")
selenia.find("password field").send_keys("secret_sauce")
selenia.find("the login button").click()

# Find all matching elements, best match first
buttons = selenia.find_all("add to cart button")
```

## 🧩 The model
The first time you create a `Selenia`, it downloads the model (about 24 MB) into `~/.cache/selenia`
and verifies its checksum. After that it runs offline.

- `SELENIA_CACHE_DIR` changes where the download is kept.
- `SELENIA_MODEL_URL` fetches from your own mirror instead of the GitHub release.
- To use a model you trained yourself, pass `LocalRanker(model_dir="training/models/selenia-ce")`
  or set `SELENIA_MODEL_DIR`. That is the folder written by `training/train.py`.

## 🎯 How matches are chosen
- `find` raises Selenium's `NoSuchElementException` when the model is not confident (`min_score`,
  default 0.5) or when two elements fit equally well (`min_margin`, default 0.05). The message
  names the candidates, so you can see what to add to the description.
- `find_all` returns every element scoring at least `min_score`, best first.
- Tune both with `LocalRanker(min_score=..., min_margin=...)`; `min_margin=0` always takes the top pick.
- iframes are not searched: switch into the frame first, then call `find`.

See [training/README.md](training/README.md) to train or improve the model on your own pages.

## 🧪 Running Tests
```bash
python -m pytest tests/
```
The tests in `tests/test_browser.py` drive a headless Chrome against a local page and are skipped
when Chrome cannot start. The ones that use the real model are also skipped unless a trained model
is at `training/models/selenia-ce` or `SELENIA_MODEL_DIR`.

## 📄 License
MIT

---

Made with ❤️ by Penielny
