# SPDX-FileCopyrightText: 2023-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


from idf_component_tools.__version__ import __version__
from idf_component_tools.file_tools import DEFAULT_EXCLUDE

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

version = __version__
project_homepage = 'https://components.espressif.com/'

author = 'Espressif Systems (Shanghai) Co., Ltd.'
languages = ['en']

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx_rtd_theme',
    'sphinx_collapse',
    'sphinx_copybutton',
    'sphinx_tabs.tabs',
    'sphinx_click',
    'sphinxcontrib.autodoc_pydantic',
    'sphinxext.rediraffe',
]
smartquotes = False
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Map old document paths (without file extensions) to new ones.
# Note: These are Sphinx "docnames" relative to this language root (docs/en/).
# Example: `guides/faq` used to live at `docs/en/guides/faq.rst`.
rediraffe_redirects = {
    # Guides -> Getting Started
    'guides/updating_component_manager': 'getting_started/updating_component_manager',
    # Guides -> Troubleshooting
    'guides/faq': 'troubleshooting/faq',
    # Guides -> Use (How-to)
    'guides/partial_mirror': 'use/how_to_partial_mirror',
    'guides/version_solver': 'use/explanation_version_solver',
}
# Make sure the target is unique
autosectionlabel_prefix_document = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# Directories are relative to the language directory
templates_path = ['../_templates']
static_path = ['../_static']
html_theme = 'sphinx_rtd_theme'
html_logo = '../_static/logo.png'
html_favicon = '../_static/favicon.ico'
html_static_path = ['../_static']
html_css_files = ['theme_overrides.css']


def _list_of_strings_to_html(list_of_strings):
    s = '<ul>'
    for string in sorted(list_of_strings):
        s += f'<li><code class="python literal">{string}</code></li>'
    s += '</ul>'
    return s


# Dynamic Values
rst_prolog = f"""
.. |DEFAULT_EXCLUDE| raw:: html

   {_list_of_strings_to_html(DEFAULT_EXCLUDE)}
"""
