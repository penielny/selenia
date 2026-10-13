"""Using Selenia inside a pytest suite.

    python -m pytest examples/test_login_pytest.py -v

The model is loaded once for the whole run (scope="session") because loading it takes a moment;
each test still gets a fresh browser.
"""
import pytest
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from selenia import LocalRanker, Selenia


@pytest.fixture(scope="session")
def ranker():
    return LocalRanker()


@pytest.fixture
def shop(ranker):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1366,900")
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.saucedemo.com/")
    yield Selenia(driver, ranker)
    driver.quit()


def log_in(shop, username, password="secret_sauce"):
    shop.find("username field").send_keys(username)
    shop.find("password field").send_keys(password)
    shop.find("the login button").click()


def test_valid_user_reaches_the_products_page(shop):
    log_in(shop, "standard_user")
    WebDriverWait(shop.driver, 10).until(lambda d: "inventory" in d.current_url)
    assert shop.find("product sort dropdown").is_displayed()


def test_locked_out_user_sees_an_error(shop):
    log_in(shop, "locked_out_user")
    assert shop.find("dismiss error button").is_displayed()
    # Selenia and ordinary locators mix freely: use a selector where you already have a good one.
    assert "locked out" in shop.driver.find_element(By.CSS_SELECTOR, "[data-test=error]").text


def test_products_page_is_not_shown_before_login(shop):
    with pytest.raises(NoSuchElementException):
        shop.find("product sort dropdown")
