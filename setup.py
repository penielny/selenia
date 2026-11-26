from setuptools import setup, find_packages

with open('README.md','r') as f:
    description = f.read()

setup(
    name="selenia",
    version="0.3.0",
    description="Find Selenium elements with plain English, using a 24 MB local model. No LLM, no API key.",
    long_description=description,
    long_description_content_type='text/markdown',
    author="Penielny",
    author_email="penielnyinaku@gmail.com",
    url="https://github.com/penielny/selenia",
    project_urls={
        "Source": "https://github.com/penielny/selenia",
        "Issues": "https://github.com/penielny/selenia/issues",
        "Examples": "https://github.com/penielny/selenia/tree/main/examples",
        "Training kit": "https://github.com/penielny/selenia/tree/main/training",
        "Changelog": "https://github.com/penielny/selenia/releases",
    },
    license="MIT",
    keywords=[
        "selenium", "test automation", "web testing", "locator", "xpath", "natural language",
        "self-healing", "qa", "onnx", "e2e testing",
    ],
    packages=find_packages(exclude=["tests", "tests.*", "training", "training.*", "examples", "examples.*"]),
    install_requires=[
        "selenium",
        "onnxruntime",
        "tokenizers",
        "numpy",
    ],
    package_data={"selenia": ["candidates.js"]},
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Framework :: Pytest",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Testing :: Acceptance",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
