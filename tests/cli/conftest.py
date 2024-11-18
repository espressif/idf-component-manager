# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import pytest
from click.testing import CliRunner

from idf_component_manager.cli.core import initialize_cli


@pytest.fixture
def invoke_cli():
    runner = CliRunner()
    return lambda *args, **kwargs: runner.invoke(initialize_cli(), args, **kwargs)
