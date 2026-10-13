"""Log in to a demo shop by describing the elements in plain English.

    python examples/01_quickstart.py

The first run downloads the model (about 24 MB) into ~/.cache/selenia.
Set HEADLESS=1 to run without opening a browser window.
"""
import os

from selenium import webdriver

from selenia import Selenia

options = webdriver.ChromeOptions()
if os.environ.get("HEADLESS"):
    options.add_argument("--headless=new")
driver = webdriver.Chrome(options=options)
selenia = Selenia(driver)

try:
    driver.get("https://www.saucedemo.com/")

    # find() returns an ordinary Selenium WebElement, so everything you already know still works.
    selenia.find("username field").send_keys("standard_user")
    selenia.find("password field").send_keys("secret_sauce")
    selenia.find("the login button").click()

    print("Logged in, now on:", driver.current_url)
finally:
    driver.quit()
