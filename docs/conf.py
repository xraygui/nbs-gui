"""Sphinx configuration for nbs-gui documentation."""

import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath("../src"))

project = "NBS-GUI"
copyright = "2024, NSLS-II"
author = "NSLS-II"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_theme",
    "myst_parser",  # For markdown support
    "sphinx_design",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# HTML output options
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pyqt": ("https://www.riverbankcomputing.com/static/Docs/PyQt6/", None),
    "pyside": ("https://doc.qt.io/qtforpython/", None),
    "ophyd": ("https://blueskyproject.io/ophyd/", None),
}

# Napoleon settings
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True

# MyST settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]