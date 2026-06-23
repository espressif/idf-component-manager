# SPDX-FileCopyrightText: 2023-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#
# English Language Sphinx config file.
#
# Uses ../conf_common.py for most non-language-specific settings.

import os
import sys

# Make the docs/ directory importable so that:
#  * the shared conf_common.py can be imported, and
#  * the ``.. click:: en.conf:compote_cli`` directive can resolve this module.
# Use a path relative to this file (not the cwd), since ESP-Docs runs Sphinx
# from the build directory rather than the project root.
_docs_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _docs_dir)

# Importing conf_common adds all the non-language-specific
# parts to this conf module
from conf_common import *  # noqa: F403, E402

from idf_component_manager.cli.core import initialize_cli  # noqa: E402

compote_cli = initialize_cli()

project = 'IDF Component Management'
copyright = '2023-2026, Espressif Systems (Shanghai) Co., Ltd.'
pdf_title = 'IDF Component Management'
language = 'en'
