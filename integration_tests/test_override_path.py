# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import textwrap

import pytest

from .integration_test_helpers import fixtures_path, project_action


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
                            'override_path': '../../',
                        },
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_reconfigure_with_invalid_override_path(project):
    res = project_action(project, 'reconfigure')
    assert 'The override_path you\'re using is pointing to directory' in res
    assert ' that is not a component.' in res
    assert 'cmake failed with exit code 1' in res


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'cmp_a': {'version': '*', 'override_path': '../components/cmp_a'},
                    },
                },
                'cmp_a': {
                    'version': '1.0.0',
                    'dependencies': {
                        'cmp_b': {'version': '*', 'override_path': '../cmp_b'},
                    },
                },
                'cmp_b': {
                    'version': '1.0.0',
                },
            }
        },
    ],
    indirect=True,
)
def test_reconfigure_with_multi_override_paths(project):
    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res


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
                            'override_path': '../../not_exists',
                        },
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_reconfigure_with_override_path_not_a_folder(project):
    res = project_action(project, 'reconfigure')
    assert 'does not point to a directory' in res


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'espressif/esp_rainmaker': {
                            'version': '1.0.0',
                        },
                    }
                },
                'espressif__esp_schedule': {
                    'dependencies': {
                        'espressif/rmaker_common': {
                            'version': '~1.4.2',
                        }
                    },
                    'version': '1.1.0',
                },
            }
        },
    ],
    indirect=True,
)
def test_copy_paste_managed_components_then_override_within_other_components(project):
    res = project_action(project, 'set-target', 'esp32s3', 'reconfigure')
    assert 'Configuring done' in res

    shutil.copytree(
        os.path.join(project, 'managed_components', 'espressif__rmaker_common'),
        os.path.join(project, 'components', 'espressif__rmaker_common'),
    )

    with open(
        os.path.join(project, 'components', 'espressif__esp_schedule', 'idf_component.yml'), 'w'
    ) as fw:
        fw.write(
            textwrap.dedent(
                """
                dependencies:
                  espressif/rmaker_common:
                    version: ~1.4.2
                    override_path: "../espressif__rmaker_common"
                version: "1.1.0"  # required to reproduce the bug, can't reproduce without "version"
                """
            )
        )

    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res
