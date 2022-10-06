# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
import sys
from io import open

import pytest

from idf_component_tools.manifest.validator import DEFAULT_KNOWN_TARGETS

from .integration_test_helpers import (
    build_project, fixtures_path, live_print_call, project_action, skip_for_idf_versions)


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'git-only-cmp': {
                            'git': 'https://github.com/espressif/example_components.git',
                            'path': 'folder-not-exist',
                            'include': 'git-only-cmp.h'
                        }
                    }
                }
            }
        }
    ],
    indirect=True)
def test_git_folder_does_not_exists(project):
    res = build_project(project)
    assert 'pathspec \'folder-not-exist\' did not match any file(s) known to git' in res


@pytest.mark.parametrize(
    'project', [
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
    indirect=True)
def test_local_dependency_with_relative_path(project):
    shutil.copytree(fixtures_path('components', 'cmp'), os.path.join(project, 'cmp'))
    res = build_project(project)
    assert 'Project build complete.' in res


@pytest.mark.parametrize(
    'project', [
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
                    }
                }
            }
        },
    ],
    indirect=True)
def test_local_dependency_main_requires(project):
    res = build_project(project)
    assert 'Project build complete.' in res


def test_known_targets():
    branch = os.getenv('IDF_BRANCH')
    if not branch or branch == 'master':
        idf_path = os.environ['IDF_PATH']
        sys.path.append(os.path.join(idf_path, 'tools'))
        from idf_py_actions.constants import PREVIEW_TARGETS, SUPPORTED_TARGETS
        assert set(SUPPORTED_TARGETS + PREVIEW_TARGETS) == set(DEFAULT_KNOWN_TARGETS)


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '==$CMP_VERSION',
                        },
                    }
                }
            }
        },
    ],
    indirect=True)
def test_env_var(project, monkeypatch):
    monkeypatch.setenv('CMP_VERSION', '3.0.3')
    real_result = project_action(project, 'reconfigure')
    assert 'example/cmp (3.0.3)' in real_result

    monkeypatch.setenv('CMP_VERSION', '3.3.3')
    real_result = project_action(project, 'reconfigure')
    assert 'example/cmp (3.3.3)' in real_result


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '*',
                            'include': 'cmp.h',
                        },
                    }
                }
            }
        },
    ],
    indirect=True)
def test_build_pure_cmake(project):
    if skip_for_idf_versions('v4.1', 'v4.2', 'v4.3'):
        return

    build_dir = os.path.join(project, 'build')
    res = live_print_call(['cmake', '-S', project, '-B', build_dir, '-G', 'Ninja'])
    assert 'Generating done' in res
    res = live_print_call(['cmake', '--build', build_dir])
    assert 'FAILED' not in res


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'cmp': {
                            'version': '*',
                            'path': fixtures_path('components', 'cmp'),
                            'include': 'cmp.h',
                            'rules': [
                                {
                                    'if': 'idf_version < 3.0'
                                },
                            ]
                        },
                    }
                }
            }
        },
    ],
    indirect=True)
def test_inject_requirements_with_optional_dependency(project):
    res = project_action(project, 'reconfigure')
    assert 'Skipping optional dependency: cmp' in res
    assert '[1/1] idf' in res
    assert 'cmake failed with exit code 1' not in res


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '3.3.7',
                        },
                    }
                }
            }
        },
    ], indirect=True)
def test_set_component_version(project):
    with open(os.path.join(project, 'CMakeLists.txt'), 'a') as fw:
        fw.write(u'\n')
        fw.write(u'idf_component_get_property(version example__cmp COMPONENT_VERSION)\n')
        fw.write(u'message("Component example__cmp version: ${version}")\n')

    res = project_action(project, 'reconfigure')
    assert 'example/cmp (3.3.7)' in res
    assert 'Component example__cmp version: 3.3.7' in res


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'idf': {
                            'version': '^6.1',
                        }
                    }
                },
                'component_foo': {
                    'version': '1.0.0',
                    'dependencies': {
                        'idf': {
                            'version': '^6.1',
                        }
                    },
                },
            }
        }
    ],
    indirect=True)
def test_root_dep_failed(project):
    res = project_action(project, 'reconfigure')
    assert 'ERROR: Because project depends on idf (^6.1) which doesn\'t match any' in res
    assert 'versions, version solving failed.' in res
    assert 'Please check manifest file of the following component(s): main,' in res
    assert 'component_foo' in res
