# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os

import pytest


@pytest.fixture()
def cmp_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..',
        'fixtures',
        'components',
        'cmp',
    )
