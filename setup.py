from setuptools import setup, find_packages

with open('README.md','r') as f:
    description = f.read()

setup(
    name="selenia",
    version="0.2.0",
    description="Selenium wrapper to find XPath from natural language using LLMs",
    long_description=description,
    long_description_content_type='text/markdown',
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
