# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
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
    assert "The override_path you're using is pointing to directory" in res
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
