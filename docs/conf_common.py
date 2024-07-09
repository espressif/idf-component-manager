# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from idf_component_tools.__version__ import __version__

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
    'sphinx.ext.autosectionlabel',
    'sphinx_click',
]
smartquotes = False
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

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
