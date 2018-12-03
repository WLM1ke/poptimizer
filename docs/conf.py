import os
import re
import sys

_package_name = "poptimizer"
_start_year = 2018
_description = "Оптимизация долгосрочного портфеля акций"
_badges = [
    {
        "image": "https://api.codacy.com/project/badge/Coverage/363c10e1d85b404882326cf62b78f25c",
        "target": "https://app.codacy.com/project/wlmike/poptimizer/dashboard",
        "height": "20",
        "alt": "Code coverage status",
    },
    {
        "image": "https://api.codacy.com/project/badge/Grade/363c10e1d85b404882326cf62b78f25c",
        "target": "https://app.codacy.com/project/wlmike/poptimizer/dashboard",
        "height": "20",
        "alt": "Code quality status",
    },
    {
        "image": "https://badge.fury.io/py/poptimizer.svg",
        "target": "https://badge.fury.io/py/poptimizer",
        "height": "20",
        "alt": "Latest PyPI package version",
    },
]

_route_path = os.path.abspath("../")
sys.path.insert(0, _route_path)
_version_path = os.path.abspath(os.path.join(_route_path, _package_name, "__init__.py"))
with open(_version_path) as file:
    try:
        _version_info = re.search(
            r"^__version__ = \""
            r"(?P<major>\d+)"
            r"\.(?P<minor>\d+)"
            r"\.(?P<patch>\d+)\"$",
            file.read(),
            re.M,
        ).groupdict()
    except IndexError:
        raise RuntimeError("Unable to determine version.")

version = "{major}.{minor}".format(**_version_info)
release = "{major}.{minor}.{patch}".format(**_version_info)

extensions = ["sphinx.ext.autodoc", "sphinx.ext.githubpages", "sphinxcontrib.asyncio"]
autodoc_member_order = "bysource"
templates_path = ["templates"]
html_static_path = ["static"]

source_suffix = ".rst"
master_doc = "index"
project = _package_name
copyright = f"{_start_year}, Mikhail Korotkov aka WLMike"
author = "Mikhail Korotkov aka WLMike"
language = "ru"
exclude_patterns = ["build"]
highlight_language = "default"
html_theme = "aiohttp_theme"

html_theme_options = {
    "logo": "",
    "description": _description,
    "canonical_url": f"https://wlm1ke.github.io/{_package_name}",
    "github_user": "WLM1ke",
    "github_repo": _package_name,
    "github_button": False,
    "github_type": "",
    "github_banner": True,
    "travis_button": True,
    "badges": _badges,
    "sidebar_collapse": False,
}

html_sidebars = {"**": ["about.html", "navigation.html"]}
