# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
from io import open

import pytest

from .integration_test_helpers import set_target


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '>=3.3.5',
                        }
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_changing_target(project):
    lock_path = os.path.join(project, 'dependencies.lock')
    res = set_target(project, 'esp32')
    assert 'Building ESP-IDF components for target esp32' in res
    with open(lock_path, mode='r', encoding='utf-8') as f:
        assert 'esp32\n' in f.read()
    res = set_target(project, 'esp32s2')
    assert 'Building ESP-IDF components for target esp32s2' in res
    assert 'Target changed from esp32 to esp32s2, solving dependencies' in res
    with open(lock_path, mode='r', encoding='utf-8') as f:
        assert 'esp32s2\n' in f.read()


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'idf': {
                            'version': '>=4.1.0',
                        }
                    },
                    'targets': ['esp32s2'],
                }
            },
        },
    ],
    indirect=True,
)
def test_idf_check_target_fail_manifest(project):
    res = set_target(project, 'esp32')
    assert 'Component "main" does not support target esp32' in res


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '0.0.1',
                        },
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_idf_check_target_fail_dependency(project):
    res = set_target(project, 'esp32')
    assert (
        'Cannot find versions of "example/cmp" satisfying "0.0.1" for the current target "esp32"'
        in res
    )


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'idf': {
                            'version': '>=4.1.0',
                        },
                        'example/cmp': {
                            'version': '3.3.3',
                        },
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_idf_check_target_pass(project):
    res = set_target(project, 'esp32')
    assert 'Build files have been written to:' in res
