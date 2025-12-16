# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from idf_component_tools.lock import LockManager
from idf_component_tools.manager import ManifestManager

from .integration_test_helpers import build_project, fixtures_path, live_print_call, project_action


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '*',
                        }
                    }
                }
            }
        }
    ],
    indirect=True,
)
def test_build_component_from_component_registry(project):
    res = build_project(project)
    assert 'Project build complete' in res


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
    res = project_action(project, 'reconfigure')
    assert "pathspec 'folder-not-exist' did not match any file(s) known to git" in res


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
        fw.write('\n')
        fw.write('idf_component_get_property(version example__cmp COMPONENT_VERSION)\n')
        fw.write('message("Component example__cmp version: ${version}")\n')

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
                            'version': '^4.9',
                        }
                    }
                },
                'component_foo': {
                    'version': '1.0.0',
                    'dependencies': {
                        'idf': {
                            'version': '^4.9',
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
    assert "Result: Because project depends on idf (^4.9) which doesn't match any" in res
    assert 'versions, version solving failed.' in res
    assert 'Please check manifest file of the following component(s): main,' in res
    assert 'component_foo' in res


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
def test_update_dependencies_outdated(project):
    shutil.copytree(fixtures_path('components', 'cmp'), os.path.join(project, 'cmp'))
    project_action(project, 'reconfigure')

    manifest_manager = ManifestManager(os.path.join(project, 'cmp'), 'cmp')
    manifest_manager.manifest.version = '1.2.0'
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
def test_update_dependencies_without_lock(project):
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


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '*',
                        },
                    }
                }
            }
        },
    ],
    indirect=True,
)
@pytest.mark.parametrize(
    'component_name, namespace_name',
    [
        ('example__cmp', 'example/cmp'),  # work with long name
        ('cmp', 'cmp'),  # also short name
    ],
)
def test_idf_build_inject_dependencies_even_with_set_components(
    project,
    component_name,
    namespace_name,
):
    project_cmake_filepath = os.path.join(project, 'CMakeLists.txt')
    with open(project_cmake_filepath) as fr:
        s = fr.read()

    with open(project_cmake_filepath, 'w') as fw:
        fw.write(s.replace('project(main)', 'set(COMPONENTS main)\nproject(main)'))

    res = project_action(project, 'reconfigure')
    assert 'Generating done' in res

    os.makedirs(os.path.join(project, 'components'))
    shutil.copytree(
        os.path.join(project, 'managed_components', 'example__cmp'),
        os.path.join(project, 'components', component_name),
    )

    project_action(project, 'fullclean')  # clean the downloaded component

    res = project_action(project, 'reconfigure')
    with open(os.path.join(project, 'dependencies.lock')) as fr:
        lock = YAML(typ='safe').load(fr)

    assert namespace_name in lock['dependencies']
    assert lock['dependencies'][namespace_name]['source']['path'] == os.path.join(
        'components', component_name
    )
    assert lock['dependencies'][namespace_name]['source']['type'] == 'local'

    # didn't download the component
    assert not os.path.isdir(os.path.join(project, 'managed_components'))


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'espressif/esp-modbus': {
                            'version': '1.0.5',
                        },
                        'espressif/mdns': {
                            'version': '1.0.7',
                        },
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_idf_reconfigure_fixed_order_sdkconfig(project):
    project_action(project, 'reconfigure')
    last_mtime = os.stat(os.path.join(project, 'sdkconfig')).st_mtime

    for _ in range(10):
        # this is to make sure that the sdkconfig file
        # won't be updated if the dependencies are not changed
        project_action(project, 'reconfigure')
        assert last_mtime == os.stat(os.path.join(project, 'sdkconfig')).st_mtime


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {},
                'component_a': {
                    'dependencies': {
                        'component_b': {
                            'path': '../component_b',
                        }
                    }
                },
                'component_b': {
                    'dependencies': {
                        'component_a': {
                            'path': '../component_a',
                        }
                    }
                },
            }
        },
    ],
    indirect=True,
)
def test_circular_dependency(project):
    res = project_action(project, 'reconfigure')
    assert 'Generating done' in res

    with open(os.path.join(project, 'dependencies.lock')) as fr:
        lock = YAML(typ='safe').load(fr)

    assert lock['dependencies']['component_a']['source']['path'] == os.path.join(
        'components', 'component_a'
    )
    assert lock['dependencies']['component_a']['source']['type'] == 'local'
    assert lock['dependencies']['component_b']['source']['path'] == os.path.join(
        'components', 'component_b'
    )
    assert lock['dependencies']['component_b']['source']['type'] == 'local'
