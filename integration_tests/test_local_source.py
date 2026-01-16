# SPDX-FileCopyrightText: 2024-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil

import pytest
from ruamel.yaml import YAML

from integration_tests.integration_test_helpers import build_project, fixtures_path, project_action


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
                            'path': '$COMP_PATH',
                        }
                    }
                }
            }
        },
        {
            'components': {
                'main': {
                    'dependencies': {
                        'cmp': {
                            'override_path': '$COMP_PATH',
                        }
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_local_dependency_with_env_var_path(project, monkeypatch):
    shutil.copytree(fixtures_path('components', 'cmp'), os.path.join(project, 'cmp'))

    monkeypatch.setenv('COMP_PATH', os.path.join('../cmp'))
    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res

    monkeypatch.delenv('COMP_PATH')
    res = project_action(project, 'reconfigure')
    assert 'ERROR: Environment variable "COMP_PATH" is not set' in res


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
@pytest.mark.xfail(
    os.getenv('IDF_COMPONENT_TESTS_BUILD_SYSTEM_VERSION') == '2',
    reason='Not all discovered components are available during injection in CMake V2',
)
def test_local_dependency_main_requires(project):
    res = build_project(project)
    assert 'Project build complete.' in res


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'path': '../example__cmp',
                            'version': '*',
                        },
                    },
                },
            }
        },
    ],
    indirect=True,
)
@pytest.mark.xfail(
    os.getenv('IDF_COMPONENT_TESTS_BUILD_SYSTEM_VERSION') == '2',
    reason='Not all discovered components are available during injection in CMake V2',
)
def test_local_dependency_reconfigure_non_existing(project):
    project_action(project, 'create-component', 'example__cmp')

    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res

    with open(os.path.join(project, 'dependencies.lock')) as f:
        lock = YAML(typ='safe').load(f)
        assert 'example/cmp' in lock['dependencies']
        assert lock['dependencies']['example/cmp']['source']['path'] == os.path.join(
            project, 'example__cmp'
        )

    # rename the folder
    with open(os.path.join(project, 'main', 'idf_component.yml')) as f:
        manifest = YAML().load(f)
        manifest['dependencies']['example/cmp']['path'] = '../cmp'

    with open(os.path.join(project, 'main', 'idf_component.yml'), 'w') as fw:
        YAML().dump(manifest, fw)

    shutil.move(os.path.join(project, 'example__cmp'), os.path.join(project, 'cmp'))

    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res
    with open(os.path.join(project, 'dependencies.lock')) as f:
        lock = YAML(typ='safe').load(f)
        assert 'example/cmp' in lock['dependencies']
        assert lock['dependencies']['example/cmp']['source']['path'] == os.path.join(project, 'cmp')
