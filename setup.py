from setuptools import setup, find_packages

with open('README.md','r') as f:
    description = f.read()

setup(
    name="selenia",
    version="0.3.0",
    description="Selenium wrapper that finds elements from natural language using a small local model",
    long_description=description,
    long_description_content_type='text/markdown',
    author="Penielny",
    author_email="penielnyinaku@gmail.com",
    packages=find_packages(),
    install_requires=[
        "selenium",
        "onnxruntime",
        "tokenizers",
        "numpy",
    ],
    package_data={"selenia": ["candidates.js"]},
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
