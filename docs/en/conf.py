# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import sys

from idf_component_manager.cli.core import initialize_cli

sys.path.insert(0, os.path.abspath('../'))
from conf_common import *  # noqa

compote_cli = initialize_cli()

project = 'IDF Component Management'
copyright = '2023, Espressif Systems (Shanghai) Co., Ltd.'
language = 'en'
