# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import shutil

import pytest

from .integration_test_helpers import current_idf_in_the_list, fixtures_path, project_action


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'cmp': {
                            'version': '*',
                            'path': fixtures_path('components', 'cmp'),
                            'include': 'cmp.h',
                            'rules': [
                                {'if': 'idf_version < 3.0'},
                            ],
                        },
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_inject_requirements_with_optional_dependency(project):
    res = project_action(project, 'reconfigure')
    assert 'Skipping optional dependency: cmp' in res
    assert '[1/1] idf' in res
    assert 'cmake failed with exit code 1' not in res


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'espressif/esp_insights': {
                            'version': '1.0.1',
                        },
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_indirect_optional_dependency(project, idf_version):
    """
    Test installation of cbor that present in IDF v4 but excluded by a rule in esp_insight
    It should be installed correctly on all IDF versions
    """

    if not current_idf_in_the_list('v4.4', 'v5.0', 'v5.1', 'v5.2'):
        logging.info('Skipping the test')
        return

    res = project_action(project, 'reconfigure')
    if 'v4.4' in idf_version:
        assert 'Skipping optional dependency: espressif/cbor' in res
    else:
        assert '[1/6] espressif/cbor' in res

    assert 'cmake failed with exit code 1' not in res


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'foo': {
                            'version': '*',
                            'path': '../foo',
                        }
                    }
                },
                # mv from components/foo to foo later
                'foo': {
                    'dependencies': {
                        'bar': {
                            'version': '*',
                            'override_path': '/non_exists',
                            'rules': [
                                {'if': 'target in [esp32p4]'},
                            ],
                        },
                    }
                },
            }
        },
    ],
    indirect=True,
)
def test_optional_dependency_with_invalid_override_path_in_deps(project):
    shutil.move(os.path.join(project, 'components', 'foo'), os.path.join(project, 'foo'))

    res = project_action(project, 'reconfigure')
    assert 'Skipping optional dependency: bar' in res
    assert 'Configuring done' in res
