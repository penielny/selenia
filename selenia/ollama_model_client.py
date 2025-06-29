import requests
import ollama


class OllamaClient:
    def __init__(self,model_name):
        self.client = ollama.Client()
        self.model = model_name

    def query_xpath(self, html, query):
        prompt = f"""
        Given the following HTML and a natural language query, return the XPath for the described element.

        HTML:
        {html[:10000]}

        Query: {query}

        XPath:
        """
        response = self.client.generate(model=self.model,prompt=prompt)
        
        if "response" in response:
            output = response["response"]
            xpath = output.split("XPath:")[-1].strip()
            return xpath
        else:
            raise ValueError("Failed to get response from Ollama model.")

        
        
class OllamaServerClient:
    def __init__(self, model_name="llama3", base_url="http://localhost:11434/api/generate"):
        self.model = model_name
        self.base_url = base_url

    def query_xpath(self, html, query):
        prompt = f"""
        Given the following HTML and a natural language query, return the XPath for the described element.

        HTML:
        {html[:10000]}

        Query: {query}

        XPath:
        """

        response = requests.post(
            self.base_url,
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
        )

        if response.status_code == 200:
            data = response.json()
            output = data.get("response", "")
            xpath = output.split("XPath:")[-1].strip()
            return xpath
        else:
            raise Exception(f"Ollama error ({response.status_code}): {response.text}")
