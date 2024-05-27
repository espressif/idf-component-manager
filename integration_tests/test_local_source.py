# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil

import pytest

from integration_tests.integration_test_helpers import build_project, fixtures_path


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'cmp': {
                            'version': '*',
                            'path': os.path.join('..', 'cmp'),
                            'include': 'cmp.h',
                        }
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_local_dependency_with_relative_path(project):
    shutil.copytree(fixtures_path('components', 'cmp'), os.path.join(project, 'cmp'))
    res = build_project(project)
    assert 'Project build complete.' in res


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'cmake_lists': {
                        'requires': 'efuse',
                    },
                    'dependencies': {
                        'example/cmp': {
                            'version': '*',
                            'path': fixtures_path('components', 'cmp'),
                            'include': 'cmp.h',
                        },
                    },
                }
            }
        },
    ],
    indirect=True,
)
def test_local_dependency_main_requires(project):
    res = build_project(project)
    assert 'Project build complete.' in res
