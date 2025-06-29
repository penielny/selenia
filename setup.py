from setuptools import setup, find_packages

setup(
    name="selenia",
    version="0.1.0",
    description="Selenium wrapper to find XPath from natural language using LLMs",
    author="Penielny",
    author_email="penielnyinaku@gmail.com",
    packages=find_packages(),
    install_requires=[
        "selenium",
        "requests",
        "ollama",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
