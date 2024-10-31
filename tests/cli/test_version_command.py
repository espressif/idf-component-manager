# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from idf_component_tools.__version__ import __version__


def test_version(invoke_cli):
    output = invoke_cli('version').output
    assert __version__ in output
