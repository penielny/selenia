"""find_all() returns every element that fits a description, best match first.

    python examples/04_find_all.py
"""
import os

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

from selenia import Selenia

options = webdriver.ChromeOptions()
options.add_argument("--window-size=1366,900")
if os.environ.get("HEADLESS"):
    options.add_argument("--headless=new")
driver = webdriver.Chrome(options=options)
selenia = Selenia(driver)

try:
    driver.get("https://www.saucedemo.com/")
    selenia.find("username field").send_keys("standard_user")
    selenia.find("password field").send_keys("secret_sauce")
    selenia.find("the login button").click()
    WebDriverWait(driver, 10).until(lambda d: "inventory" in d.current_url)

    buttons = selenia.find_all("add to cart button")
    print(f"Found {len(buttons)} 'Add to cart' buttons")
    for button in buttons:
        button.click()

    # Each click turned its button into "Remove", so look them up again by the new text.
    print(f"Cart now has {len(selenia.find_all('remove button'))} items")
finally:
    driver.quit()
