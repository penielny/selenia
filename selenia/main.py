from .local_ranker import LocalRanker

class Selenia:
    def __init__(self, driver, model_client=None):
        self.driver = driver
        self.model_client = model_client or LocalRanker()

    def find(self, description: str):
        """Find an element using a natural language description."""
        return self.model_client.locate(self.driver, description)

    def find_all(self, description: str):
        """Find all matching elements using a natural language description."""
        return self.model_client.locate_all(self.driver, description)
