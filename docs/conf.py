"""Sphinx configuration for jellycell documentation."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

# -- Project information -----------------------------------------------------

project = "jellycell"
author = "Blaise"
copyright = "2026, Blaise and jellycell contributors"

try:
    release = _dist_version("jellycell")
except PackageNotFoundError:
    release = "0.0.1"
version = ".".join(release.split(".")[:2])

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.intersphinx",
    "myst_parser",
    "autodoc2",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinxcontrib.typer",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

master_doc = "index"
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    # autodoc2 generates its own index.rst; we use our hand-written docs/api/index.md instead.
    "apidocs/index.rst",
]

# -- autodoc2 ---------------------------------------------------------------

autodoc2_packages = [
    {
        "path": "../src/jellycell",
        "module": "jellycell",
    },
]
autodoc2_render_plugin = "myst"
autodoc2_output_dir = "apidocs"
autodoc2_hidden_objects = {"dunder", "private", "inherited"}
autodoc2_skip_module_regexes = [r"jellycell\.__main__"]

# -- MyST --------------------------------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
    "linkify",
    "substitution",
]
myst_heading_anchors = 3

# -- HTML output -------------------------------------------------------------

html_theme = "furo"
html_title = f"jellycell {version}"
html_theme_options = {
    "source_repository": "https://github.com/random-walks/jellycell",
    "source_branch": "main",
    "source_directory": "docs/",
    "sidebar_hide_name": False,
}

# -- Intersphinx -------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
    "jupytext": ("https://jupytext.readthedocs.io/en/latest", None),
    "nbformat": ("https://nbformat.readthedocs.io/en/stable", None),
    "jupyter-client": ("https://jupyter-client.readthedocs.io/en/stable", None),
}

# -- sphinx-copybutton -------------------------------------------------------

copybutton_prompt_text = r"^\$ |^> "
copybutton_prompt_is_regexp = True

# -- Nitpicky ----------------------------------------------------------------

nitpicky = False  # flip to True once API is stable (Phase 6)
