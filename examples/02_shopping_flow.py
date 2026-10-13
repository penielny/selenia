"""A full test flow: log in, add a product to the cart, and check out.

    python examples/02_shopping_flow.py

Shows how to tell repeated elements apart: the page has six "Add to cart" buttons, so the
description names the product.
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


def wait_for_page(name):
    WebDriverWait(driver, 10).until(lambda d: name in d.current_url)


try:
    driver.get("https://www.saucedemo.com/")
    selenia.find("username field").send_keys("standard_user")
    selenia.find("password field").send_keys("secret_sauce")
    selenia.find("the login button").click()
    wait_for_page("inventory")

    # "add to cart button" alone would be ambiguous here; naming the product picks one.
    selenia.find("add the backpack to the cart").click()
    selenia.find("cart button in the header").click()
    wait_for_page("cart")

    selenia.find("checkout button").click()
    wait_for_page("checkout-step-one")

    selenia.find("first name field").send_keys("Ama")
    selenia.find("last name").send_keys("Mensah")
    selenia.find("zip code field").send_keys("00233")
    selenia.find("continue button").click()
    wait_for_page("checkout-step-two")

    selenia.find("finish button").click()
    wait_for_page("checkout-complete")

    message = selenia.find("the thank you heading").text
    print("Order placed:", message)
    assert "Thank you" in message
finally:
    driver.quit()
