# Selenia examples

Each script runs against [saucedemo.com](https://www.saucedemo.com/), a public demo shop made for
test automation. You need Chrome installed.

```bash
pip install selenia
python examples/01_quickstart.py
```

The first run downloads the model (about 24 MB) into `~/.cache/selenia`; after that it starts
straight away. A browser window opens so you can watch. Set `HEADLESS=1` to hide it:

```bash
HEADLESS=1 python examples/02_shopping_flow.py
```

| File | What it shows |
|---|---|
| [01_quickstart.py](01_quickstart.py) | The smallest useful script: log in with three `find()` calls. |
| [02_shopping_flow.py](02_shopping_flow.py) | A full flow from login to a placed order, including picking one of six identical "Add to cart" buttons by naming the product. |
| [03_no_match_and_ambiguity.py](03_no_match_and_ambiguity.py) | What `find()` raises when nothing fits or when several elements fit, how to fix each, and how to look at the scores yourself. |
| [04_find_all.py](04_find_all.py) | `find_all()` to act on every matching element. |
| [test_login_pytest.py](test_login_pytest.py) | Selenia in a pytest suite, loading the model once per run. Run with `python -m pytest examples/test_login_pytest.py -v`. |

## Writing descriptions that work

- **Say what a person would see.** "the login button", "username field", "checkout button".
- **Name the thing next to a repeated element.** "add the backpack to the cart" picks one button;
  "add to cart button" is ambiguous when there are six.
- **Add where it is when that helps.** "cart button in the header".
- **When a description fails, read the error.** It names the best candidates and their scores, so
  you can see which words the model was missing. `03_no_match_and_ambiguity.py` shows how to print
  the scores for any description.
- **Mix in ordinary locators.** `find()` returns a normal Selenium `WebElement` and `selenia.driver`
  is your normal driver, so use a CSS selector wherever you already have a good one.

## Using a model you trained

```python
from selenia import Selenia, LocalRanker

selenia = Selenia(driver, LocalRanker(model_dir="training/models/selenia-ce"))
```

or set `SELENIA_MODEL_DIR` to that folder. See [../training/README.md](../training/README.md).
