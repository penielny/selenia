# Selenia

Selenium wrapper to find XPath from natural language using LLMs

---

## 🚀 Overview
Selenia lets you locate web elements using natural language queries, powered by LLMs (Large Language Models). It integrates with Selenium and supports local LLMs via Ollama.

## ✨ Features
- 🔍 Find elements by describing them in plain English
- 🤖 Pluggable LLM model clients (Ollama, OpenAI, etc.)
- 🧪 Easy integration with Selenium WebDriver
- 🧩 Extensible for custom model backends

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
from selenia import Selenia, OllamaServerClient, OllamaClient

#for either remote or local ollama server
driver = webdriver.Chrome()
model_client = OllamaServerClient(model_name="llama3",base_url="http://localhost:11434/api/generate")

#for local ollama 
model_client = OllamaClient(model_name="llama3")

selenia = Selenia(driver, model_client)

# Find an element by description
element = selenia.find("the search input box at the top bar")

# Find all matching elements
elements = selenia.find_all("all buttons with the text 'Submit'")
```

## 🧩 Model Clients
- **OllamaServerClient**: Connects to a local Ollama server (defaults: [`model_name`:`llama3`,`base_url`=`http://localhost:11434/api/generate`])
- **OllamaClient**: Uses the Ollama Python package

## 🧪 Running Tests
```bash
pytest tests/
```

## 📄 License
MIT

---

Made with ❤️ by Penielny
