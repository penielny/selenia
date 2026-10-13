"""What happens when Selenia is not sure, and how to control it.

    python examples/03_no_match_and_ambiguity.py

find() refuses to guess. It raises Selenium's NoSuchElementException when
  * nothing on the page fits the description well enough (min_score, default 0.5), or
  * two elements fit about equally well (min_margin, default 0.05).
The message names the candidates, so you can see what to add to the description.
"""
import os

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait

from selenia import LocalRanker, Selenia
from selenia.features import element_to_text

options = webdriver.ChromeOptions()
options.add_argument("--window-size=1366,900")
if os.environ.get("HEADLESS"):
    options.add_argument("--headless=new")
driver = webdriver.Chrome(options=options)
ranker = LocalRanker()
selenia = Selenia(driver, ranker)

try:
    driver.get("https://www.saucedemo.com/")
    selenia.find("username field").send_keys("standard_user")
    selenia.find("password field").send_keys("secret_sauce")
    selenia.find("the login button").click()
    WebDriverWait(driver, 10).until(lambda d: "inventory" in d.current_url)

    # 1. Nothing on the page matches.
    try:
        selenia.find("the newsletter signup checkbox")
    except NoSuchElementException as e:
        print("1. No match:\n  ", e.msg[:160], "\n")

    # 2. Six buttons match equally well.
    try:
        selenia.find("add to cart button")
    except NoSuchElementException as e:
        print("2. Ambiguous:\n  ", e.msg[:160], "\n")

    # 3. Fix it by adding detail...
    button = selenia.find("add the bike light to the cart")
    print("3. With more detail:", button.get_attribute("name"), "\n")

    # 4. ...or tell Selenia to always take the top pick when any of them will do.
    relaxed = Selenia(driver, LocalRanker(scorer=ranker.scorer, min_margin=0))
    print("4. With min_margin=0:", relaxed.find("add to cart button").get_attribute("name"), "\n")

    # 5. See the scores yourself. Handy when choosing thresholds or wording a description.
    print("5. Top 3 for 'product sort dropdown':")
    for score, element in ranker.rank(driver, "product sort dropdown")[:3]:
        print(f"   {score:.2f}  {element_to_text(element)[:90]}")
finally:
    driver.quit()
