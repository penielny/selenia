from selenium.webdriver.common.by import By

class Selenia:
    def __init__(self, driver, model_client):
        self.driver = driver
        self.model_client = model_client

    def find(self, description: str):
        """Find an element using a natural language description."""
        html = self.driver.page_source
        xpath = self.model_client.query_xpath(html, description)
        return self.driver.find_element(By.XPATH, xpath)

    def find_all(self, description: str):
        """Find all matching elements using a natural language description."""
        html = self.driver.page_source
        xpath = self.model_client.query_xpath(html, description)
        return self.driver.find_elements(By.XPATH, xpath)
