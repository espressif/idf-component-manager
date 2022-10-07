# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import pytest

from .integration_test_helpers import fixtures_path, project_action


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'cmp': {
                            'version': '*',
                            'path': fixtures_path('components', 'cmp'),
                            'override_path': '../../'
                        },
                    }
                }
            }
        },
    ],
    indirect=True)
def test_reconfigure_with_invalid_override_path(project):
    res = project_action(project, 'reconfigure')
    assert 'The override_path you\'re using is pointing to directory' in res
    assert ' that is not a component.' in res
    assert 'cmake failed with exit code 1' in res
