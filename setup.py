import re

from setuptools import setup, find_packages

REPO = "https://github.com/penielny/selenia"

with open('README.md','r') as f:
    description = f.read()

# The README uses repo-relative paths so it renders on every GitHub branch. PyPI can't resolve
# those, so point them at main: images at the raw file, links at the GitHub page.
description = re.sub(r'src="(?!https?:|#)([^"]+)"',
                     rf'src="https://raw.githubusercontent.com/penielny/selenia/main/\1"', description)
description = re.sub(r'\]\((?!https?:|#)([^)]+)\)', rf']({REPO}/blob/main/\1)', description)

setup(
    name="selenia",
    version="0.3.1",
    description="Find Selenium elements with plain English, using a 24 MB local model. No LLM, no API key.",
    long_description=description,
    long_description_content_type='text/markdown',
    author="Penielny",
    author_email="penielnyinaku@gmail.com",
    url=REPO,
    project_urls={
        "Source": REPO,
        "Issues": f"{REPO}/issues",
        "Examples": f"{REPO}/tree/main/examples",
        "Training kit": f"{REPO}/tree/main/training",
        "Changelog": f"{REPO}/releases",
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
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
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
