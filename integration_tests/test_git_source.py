# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil

import pytest

from integration_tests.integration_test_helpers import fixtures_path, project_action


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'cmp': {
                            'git': '$COMP_REPO',
                            'path': '$COMP_PATH',
                            'version': 'd7eaa77b891a624995c7e641554168bc3383433d',
                        }
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_git_dependency_with_env_var_path(project, monkeypatch):
    shutil.copytree(fixtures_path('components', 'cmp'), os.path.join(project, 'cmp'))

    monkeypatch.setenv('COMP_REPO', 'https://github.com/espressif/esp-protocols.git')
    monkeypatch.setenv('COMP_PATH', 'components/mdns')
    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res
    assert 'mdns.c' in os.listdir(os.path.join(project, 'managed_components', 'cmp'))

    # same dependencies.lock, same component path since abs path is locked
    monkeypatch.setenv('COMP_PATH', 'components/esp_mqtt_cxx')
    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res
    assert 'mdns.c' in os.listdir(os.path.join(project, 'managed_components', 'cmp'))
    assert 'esp_mqtt_cxx.cpp' not in os.listdir(os.path.join(project, 'managed_components', 'cmp'))

    # new dependencies.lock, new component path
    os.remove(os.path.join(project, 'dependencies.lock'))
    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res
    assert 'mdns.c' not in os.listdir(os.path.join(project, 'managed_components', 'cmp'))
    assert 'esp_mqtt_cxx.cpp' in os.listdir(os.path.join(project, 'managed_components', 'cmp'))

    # raise errors
    monkeypatch.delenv('COMP_REPO')
    monkeypatch.delenv('COMP_PATH')
    res = project_action(project, 'reconfigure')
    assert 'ERROR: Environment variable "COMP_REPO" is not set' in res
