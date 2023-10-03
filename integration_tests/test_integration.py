# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import shutil
import sys
from io import open
from pathlib import Path

import pytest

from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import ManifestManager
from idf_component_tools.manifest.constants import DEFAULT_KNOWN_TARGETS

from .integration_test_helpers import (
    build_project,
    current_idf_in_the_list,
    fixtures_path,
    live_print_call,
    project_action,
)


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'git-only-cmp': {
                            'git': 'https://github.com/espressif/example_components.git',
                            'path': 'folder-not-exist',
                            'include': 'git-only-cmp.h',
                        }
                    }
                }
            }
        }
    ],
    indirect=True,
)
def test_git_folder_does_not_exists(project):
    res = build_project(project)
    assert 'pathspec \'folder-not-exist\' did not match any file(s) known to git' in res


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


def test_known_targets():
    branch = os.getenv('IDF_BRANCH')
    if not branch or branch == 'master':
        idf_path = os.environ['IDF_PATH']
        sys.path.append(os.path.join(idf_path, 'tools'))
        from idf_py_actions.constants import PREVIEW_TARGETS, SUPPORTED_TARGETS

        assert set(SUPPORTED_TARGETS + PREVIEW_TARGETS) == set(DEFAULT_KNOWN_TARGETS)


@pytest.mark.parametrize(
    'project',
    [
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
    indirect=True,
)
def test_env_var(project, monkeypatch):
    monkeypatch.setenv('CMP_VERSION', '3.0.3')
    real_result = project_action(project, 'reconfigure')
    assert 'example/cmp (3.0.3)' in real_result

    monkeypatch.setenv('CMP_VERSION', '3.3.3')
    real_result = project_action(project, 'reconfigure')
    assert 'example/cmp (3.3.3)' in real_result


@pytest.mark.parametrize(
    'project',
    [
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
    indirect=True,
)
def test_build_pure_cmake(project):
    if current_idf_in_the_list('v4.2', 'v4.3'):
        logging.info('Skipping the test')

        return

    build_dir = os.path.join(project, 'build')
    res = live_print_call(['cmake', '-S', project, '-B', build_dir, '-G', 'Ninja'])
    assert 'Generating done' in res
    res = live_print_call(['cmake', '--build', build_dir])
    assert 'FAILED' not in res


@pytest.mark.parametrize(
    'project',
    [
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
    ],
    indirect=True,
)
def test_set_component_version(project):
    with open(os.path.join(project, 'CMakeLists.txt'), 'a') as fw:
        fw.write(u'\n')
        fw.write(u'idf_component_get_property(version example__cmp COMPONENT_VERSION)\n')
        fw.write(u'message("Component example__cmp version: ${version}")\n')

    res = project_action(project, 'reconfigure')
    assert 'example/cmp (3.3.7)' in res
    assert 'Component example__cmp version: 3.3.7' in res


@pytest.mark.parametrize(
    'project',
    [
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
    indirect=True,
)
def test_root_dep_failed(project):
    res = project_action(project, 'reconfigure')
    assert 'ERROR: Because project depends on idf (^6.1) which doesn\'t match any' in res
    assert 'versions, version solving failed.' in res
    assert 'Please check manifest file of the following component(s): main,' in res
    assert 'component_foo' in res


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_add_dependency(project):
    res = project_action(project, 'add-dependency', 'example/cmp^3.3.8')
    assert 'Successfully added dependency "example/cmp^3.3.8" to component "main"' in res


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_add_dependency_with_path(project):
    path = os.path.join(project, 'project', 'src')
    os.makedirs(path)
    res = project_action(project, 'add-dependency', '--path', path, 'lvgl/lvgl>=8.*')
    assert 'Successfully added dependency "lvgl/lvgl>=8.*" to component "src"' in res


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_create_manifest(project):
    res = project_action(project, 'create-manifest')
    path = os.path.join(project, 'main', 'idf_component.yml')
    assert 'Created "{}"'.format(path) in res


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_create_manifest_with_path(project):
    res = project_action(project, 'create-manifest', '--path', project)
    path = os.path.join(project, 'idf_component.yml')
    assert 'Created "{}"'.format(path) in res


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {'version': '*'},
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_check_remove_managed_component(project):
    path = Path(project) / 'managed_components'
    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res
    assert path.is_dir()
    res = project_action(project, 'fullclean')
    assert 'Executing action: remove_managed_components' in res
    assert not path.is_dir()


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
def test_update_dependencies_outdated(project, monkeypatch):
    shutil.copytree(fixtures_path('components', 'cmp'), os.path.join(project, 'cmp'))
    project_action(project, 'reconfigure')

    manifest_manager = ManifestManager(os.path.join(project, 'cmp'), 'cmp')
    manifest_manager.manifest_tree['version'] = '1.2.0'
    manifest_manager.dump(os.path.join(project, 'cmp'))

    lock = LockManager(os.path.join(project, 'dependencies.lock'))

    project_action(project, 'update-dependencies')
    assert lock.load().dependencies[0].version == '1.2.0'


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
def test_update_dependencies_without_lock(project, monkeypatch):
    shutil.copytree(fixtures_path('components', 'cmp'), os.path.join(project, 'cmp'))
    lock = LockManager(os.path.join(project, 'dependencies.lock'))

    assert not lock.load().manifest_hash  # Empty lock file

    project_action(project, 'update-dependencies')

    assert lock.load().dependencies[0].version == '1.0.0'


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/boobobobob': {
                            'version': '0.0.1',
                        },
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_idf_reconfigure_dependency_doesnt_exist(project):
    res = project_action(project, 'reconfigure')
    assert 'Component "example/boobobobob" not found' in res
