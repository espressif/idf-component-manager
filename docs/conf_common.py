# SPDX-FileCopyrightText: 2023-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#
# Common (non-language-specific) configuration for ESP-Docs / Sphinx.
#
# This file is imported by the language-specific conf.py files (e.g. en/conf.py)
# and builds on top of ESP-Docs' shared configuration.
# See https://docs.espressif.com/projects/esp-docs/en/latest/index.html

import os
import re

from esp_docs.conf_docs import *  # noqa: F403

# Explicitly import the base values we extend in place, so linters and the
# type checker know they are defined.
from esp_docs.conf_docs import extensions, html_context

from idf_component_tools.__version__ import __version__
from idf_component_tools.file_tools import DEFAULT_EXCLUDE

# -- Project information -----------------------------------------------------

version = __version__
project_homepage = 'https://components.espressif.com/'
author = 'Espressif Systems (Shanghai) Co., Ltd.'
languages = ['en']

# -- General configuration ---------------------------------------------------

# ESP-Docs already provides a base set of extensions (see esp_docs.conf_docs).
# Here we only add the ones specific to this project.
extensions += [
    'sphinx_collapse',
    'sphinx_copybutton',
    'sphinx_tabs.tabs',
    'sphinx_click',
    'sphinxcontrib.autodoc_pydantic',
]

smartquotes = False

# Make sure the autosectionlabel target is unique
autosectionlabel_prefix_document = True

# -- ESP-Docs / sphinx_idf_theme options -------------------------------------

# link roles config (used by esp_docs.esp_extensions.link_roles)
github_repo = 'espressif/idf-component-manager'

# context used by sphinx_idf_theme
html_context['github_user'] = 'espressif'
html_context['github_repo'] = 'idf-component-manager'

# Path to the project's _static folder (relative to the language conf dir)
html_static_path = ['../_static']

# Favicon for the docs. ESP-Docs forces the Espressif corporate logo for the
# sidebar (html_logo), but it does not override the favicon, so we keep our own.
html_favicon = '../_static/favicon.ico'

# Path to the project's _templates folder (relative to the language conf dir)
templates_path = ['../_templates']

# Extra project-specific CSS, loaded after the ESP-Docs defaults
html_css_files = ['theme_overrides_component_manager.css']

# Short name of the project, used as a URL slug
# (e.g. https://docs.espressif.com/projects/idf-component-manager/)
project_slug = 'idf-component-manager'

# Final PDF filename will contain the version
pdf_file_prefix = 'idf-component-manager'

# -- Redirects ---------------------------------------------------------------
# Old documents are redirected to new ones via the ESP-Docs html_redirects
# extension. Mappings live in docs/page_redirects.txt (one "old new" pair per
# line, docnames relative to the language root, without the .rst extension).
# Resolve the file relative to this config file, since ESP-Docs runs Sphinx
# from the build directory rather than the project root.
_conf_common_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_conf_common_dir, 'page_redirects.txt'), encoding='utf-8') as f:
    lines = [
        re.sub(' +', ' ', line.strip()) for line in f if line.strip() and not line.startswith('#')
    ]
    for line in lines:
        if not re.match(r'^[^\s]+ [^\s]+$', line):
            raise RuntimeError(f'Invalid line in page_redirects.txt: {line}')
    html_redirect_pages = [tuple(line.split(' ')) for line in lines]


# -- Dynamic values ----------------------------------------------------------


def _list_of_strings_to_html(list_of_strings):
    s = '<ul>'
    for string in sorted(list_of_strings):
        s += f'<li><code class="python literal">{string}</code></li>'
    s += '</ul>'
    return s


rst_prolog = f"""
.. |DEFAULT_EXCLUDE| raw:: html

   {_list_of_strings_to_html(DEFAULT_EXCLUDE)}
"""
