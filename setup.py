"""Программа установки пакета"""
import pathlib
import re
import sys

import setuptools

name = "poptimizer"
description = "Оптимизация долгосрочного портфеля акций"
python_minimal = "3.7"
status = "Development Status :: 3 - Alpha"

if sys.version_info < tuple(int(i) for i in python_minimal.split(".")):
    raise RuntimeError(f"{name} requires Python {python_minimal}+")

with open(pathlib.Path(__file__).parent / "poptimizer" / "__init__.py") as file:
    try:
        version = re.search(r"^__version__ = \"(.+)\"$", file.read(), re.M)[1]
    except IndexError:
        raise RuntimeError("Unable to determine version.")

with open("README.rst") as file:
    long_description = file.read()

setuptools.setup(
    name=name,
    version=version,
    description=description,
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url=f"https://wlm1ke.github.io/{name}/",
    author="Mikhail Korotkov aka WLMike",
    author_email="wlmike@gmail.com",
    license="http://unlicense.org",
    classifiers=[
        status,
        "Environment :: Other Environment",
        "Framework :: AsyncIO",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: Public Domain",
        "Natural Language :: Russian",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Office/Business :: Financial",
    ],
    keywords="robust portfolio optimization risk-management machine-learning moex dividends",
    project_urls={"Source": f"https://github.com/WLM1ke/{name}"},
    packages=setuptools.find_packages(exclude=["*.tests"]),
    install_requires=[
        "aiomoex",
        "pandas",
        "numpy",
        "lmdb",
        "openpyxl",
        "hyperopt",
        "catboost",
        "xlrd",
        "matplotlib",
        "reportlab",
        "bs4",
    ],
    python_requires=f">={python_minimal}",
)
