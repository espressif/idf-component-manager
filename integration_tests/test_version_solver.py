# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil
from pathlib import Path

import pytest
import yaml

from idf_component_tools.semver import Version
from integration_tests.integration_test_helpers import (
    assert_dependency_version,
    build_project,
    project_action,
)


@pytest.mark.parametrize(
    'project,result',
    [
        (
            {
                'components': {
                    'main': {
                        'dependencies': {
                            'test/circular_dependency_a': {
                                'version': '>=1.0.0',
                            }
                        }
                    }
                }
            },
            [
                'test/circular_dependency_a (1.0.0)',
            ],
        ),
        (
            {
                'components': {
                    'main': {
                        'dependencies': {
                            'test/diamond_dependency_a': {
                                'version': '*',
                            },
                            'test/diamond_dependency_b': {
                                'version': '*',
                            },
                        }
                    }
                }
            },
            [
                'test/diamond_dependency_a (1.0.0)',
                'test/diamond_dependency_b (2.0.0)',
                'test/diamond_dependency_c (3.0.0)',
            ],
        ),
        (
            {
                'components': {
                    'main': {
                        'dependencies': {
                            'test/partial_satisfy_c': {
                                'version': '*',
                            },
                            'test/partial_satisfy_y': {
                                'version': '^2.0.0',
                            },
                        }
                    }
                }
            },
            [
                'test/partial_satisfy_c (1.0.0)',
                'test/partial_satisfy_y (2.0.0)',
            ],
        ),
        (
            {
                'components': {
                    'main': {
                        'dependencies': {
                            'test/rollback_sequence_a': {
                                'version': '*',
                            }
                        }
                    }
                }
            },
            [
                'test/rollback_sequence_a (2.0.0)',
                'test/rollback_sequence_b (1.0.0)',
                'test/rollback_sequence_c (2.0.0)',
            ],
        ),
    ],
    indirect=True,
)
def test_version_solver(project, result):
    project_path = os.path.join(os.path.dirname(__file__), 'version_solver_projects', project)
    real_result = project_action(project_path, 'fullclean', 'reconfigure')
    for line in result:
        assert line in real_result


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'git-only-cmp': {
                            'version': 'main',
                            'git': 'https://github.com/espressif/example_components.git',
                            'path': 'git-only-cmp',
                            'include': 'git-only-cmp.h',
                        }
                    }
                }
            }
        },
        {
            'components': {
                'main': {
                    'dependencies': {'example/cmp': {'version': '^3.3.0~0', 'include': 'cmp.h'}}
                }
            }
        },
        {
            'components': {
                'main': {
                    'dependencies': {
                        'new+compo.nent': {
                            'include': 'new+compo.nent.h',
                        },
                        'example/cmp': {'version': '^3.3.0', 'include': 'cmp.h'},
                    }
                },
                'new+compo.nent': {
                    'cmake_lists': {
                        'priv_requires': 'cmp',
                    },
                },
            },
        },
    ],
    indirect=True,
)
def test_single_dependency(project):
    res = build_project(project)
    assert 'Project build complete.' in res


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'idf': {
                            'version': '<4.1',
                        }
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_idf_version_dependency_failed(project):
    res = project_action(project, 'reconfigure')

    assert (
        ('project depends on idf' in res and 'version solving failed.' in res)
        or
        # idf release v4.4 components/freemodbus depends on idf >= 4.1
        (
            'project depends on both idf (>=4.1) and idf (<4.1)' in res
            and 'version solving failed.' in res
        )
    )


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'idf': {
                            'version': '>=4.1',
                        }
                    }
                }
            }
        }
    ],
    indirect=True,
)
def test_idf_version_dependency_passed(project):
    res = build_project(project)
    assert 'Project build complete.' in res


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'component_foo': {
                            'path': '../../component_foo',
                        }
                    }
                },
                'component_foo': {
                    'dependencies': {
                        'git-only-cmp': {
                            'version': 'main',
                            'git': 'https://github.com/espressif/example_components.git',
                            'path': 'git-only-cmp',
                        }
                    },
                },
            }
        }
    ],
    indirect=True,
)
def test_version_solver_on_local_components_basic(project):
    # need to move to another folder, not under the default `components/`
    project = Path(project)
    (project / 'components' / 'component_foo').rename(project.parent / 'component_foo')
    real_result = project_action(project, 'fullclean', 'reconfigure')
    for line in [
        '[1/4] component_foo',
        '[2/4] example/cmp',
        '[3/4] git-only-cmp',
        '[4/4] idf',
    ]:
        assert line in real_result

    assert 'error' not in project_action(project, 'reconfigure')


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'es8311': {
                            'version': '^0.0.2-alpha',
                        }
                    },
                }
            }
        },
    ],
    indirect=True,
)
def test_version_solver_with_caret_and_prerelease(project):
    real_result = project_action(project, 'fullclean', 'reconfigure')
    for line in ['[1/2] espressif/es8311', '[2/2] idf']:
        assert line in real_result


@pytest.mark.parametrize(
    'project',
    [
        ({
            'components': {
                'main': {
                    'dependencies': {
                        'test/circular_dependency_b': {
                            'version': '*',
                        },
                        'test/circular_dependency_a': {
                            'path': '../test__circular_dependency_a',
                        },
                    }
                },
                'test__circular_dependency_a': {
                    'version': '1.0.0',
                },
            }
        }),
    ],
    indirect=True,
)
def test_version_solver_on_local_components_higher_priority(project):
    # need to move to another folder, not under the default `components/`
    os.rename(
        os.path.join(project, 'components', 'test__circular_dependency_a'),
        os.path.join(project, 'test__circular_dependency_a'),
    )
    real_result = project_action(project, 'fullclean', 'reconfigure')
    for line in [
        '[1/3] test/circular_dependency_a (*)',
        '[2/3] test/circular_dependency_b (1.0.0)',
        '[3/3] idf',
    ]:
        assert line in real_result

    with open(os.path.join(project, 'dependencies.lock')) as fr:
        d = yaml.safe_load(fr)
        assert d['dependencies']['test/circular_dependency_a'] == {
            'dependencies': [],
            'source': {
                'path': os.path.join(project, 'test__circular_dependency_a'),
                'type': 'local',
            },
            'version': '*',
        }


@pytest.mark.parametrize(
    'project',
    [
        ({
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '*',
                        }
                    }
                }
            }
        }),
    ],
    indirect=True,
)
def test_version_solver_on_local_components_with_higher_versions(project):
    real_result = project_action(project, 'reconfigure')
    for line in [
        '[1/2] example/cmp',
        '[2/2] idf',
    ]:
        assert line in real_result

    # move the example/cmp to components folder, modify the manifest version
    shutil.move(
        os.path.join(project, 'managed_components', 'example__cmp'),
        os.path.join(project, 'components', 'example__cmp'),
    )
    with open(os.path.join(project, 'components', 'example__cmp', 'idf_component.yml')) as fr:
        d = yaml.safe_load(fr)

    with open(os.path.join(project, 'components', 'example__cmp', 'idf_component.yml'), 'w') as fw:
        v = Version(d['version'])
        v.major += 1
        new_version = str(v)
        d['version'] = new_version
        yaml.safe_dump(d, fw)

    # update the dependency
    with open(os.path.join(project, 'main', 'idf_component.yml')) as fr:
        d = yaml.safe_load(fr)

    with open(os.path.join(project, 'main', 'idf_component.yml'), 'w') as fw:
        d['dependencies']['example/cmp']['version'] = new_version
        yaml.safe_dump(d, fw)

    # compile again
    output = project_action(project, 'reconfigure')
    assert 'Configuring done' in output


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {'version': '==3.3.3'},
                    }
                },
            },
        }
    ],
    indirect=True,
)
def test_version_is_not_updated_when_not_necessary(project):
    output = project_action(project, 'reconfigure')
    assert 'example/cmp (3.3.3)' in output
    assert 'Configuring done' in output
    with open(os.path.join(project, 'dependencies.lock')) as fr:
        d = yaml.safe_load(fr)
        assert d['dependencies']['example/cmp']['version'] == '3.3.3'

    # Check that the version is not updated when it is not necessary
    output = project_action(project, 'reconfigure')
    assert 'example/cmp (3.3.3)' in output
    assert 'Configuring done' in output


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {'version': '>=3.3.3'},
                    }
                },
            },
        }
    ],
    indirect=True,
)
def test_check_for_newer_component_versions(project, tmp_path, monkeypatch, fixtures_path):
    monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', 'file://' + str(tmp_path))
    monkeypatch.setenv('IDF_COMPONENT_CHECK_NEW_VERSION', '1')

    tmp_dir = tmp_path / 'components' / 'example'
    os.makedirs(str(tmp_dir))
    json_path = str(tmp_dir / 'cmp.json')

    # Move the archive to the tmp_path
    shutil.copy(
        str(fixtures_path / 'archives' / 'cmp_1.0.0.tar.gz'), str(tmp_path / 'cmp_1.0.0.tar.gz')
    )

    # Copy registry json to tmp
    shutil.copy(str(fixtures_path / 'component_jsons' / 'cmp.json'), json_path)

    # Reconfigure for the first time
    output = project_action(project, 'reconfigure')
    assert 'Configuring done' in output

    # Remove old cmp.json
    os.remove(json_path)

    # Copy json with new version
    shutil.copy(str(fixtures_path / 'component_jsons' / 'cmp_new_version.json'), json_path)

    # Check that the version is not updated when it is not necessary
    output = project_action(project, 'reconfigure')
    assert 'Following dependencies have new versions available:' in output
    assert 'Dependency "example/cmp": "3.3.99" -> "3.4.0"' in output
    assert 'Consider running "idf.py update-dependencies" to update your lock file.' in output


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {'version': '==3.3.3'},
                        'test/cmp2': {'version': '*'},
                    }
                },
            },
        }
    ],
    indirect=True,
)
def test_multiple_storage_urls(monkeypatch, project):
    fixtures = os.path.join(os.path.dirname(__file__), 'fixtures')
    monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', f'file://{fixtures};default')
    output = project_action(project, 'reconfigure')

    assert 'Configuring done' in output
    assert 'example/cmp (3.3.3)' in output
    assert 'test/cmp2 (1.0.0) from file:///' in output


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'usb_host_ch34x_vcp': {'version': '^2'},
                        'usb_host_cp210x_vcp': {'version': '^2'},
                        'usb_host_ftdi_vcp': {'version': '^2'},
                        'usb_host_vcp': {'version': '^1'},
                    }
                },
            },
        }
    ],
    indirect=True,
)
@pytest.mark.skipif(
    (os.getenv('IDF_BRANCH', 'master') or 'master') != 'master',
    reason='only test it in master branch',
)
def test_complex_version_solving(monkeypatch, project):
    output = project_action(project, 'reconfigure')
    assert 'version solving failed' in output

    shutil.rmtree(os.path.join(project, 'build'))
    output = project_action(project, '--preview', 'set-target', 'esp32p4', 'reconfigure')
    assert 'Configuring done' in output


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {'version': '*'},
                        'foo': {'path': '../foo'},
                    }
                },
                'foo': {
                    'dependencies': {
                        'espressif/esp_wrover_kit': {
                            'version': '*',
                            'rules': [
                                {'if': 'target in [esp32]'},
                            ],
                        },
                    }
                },
            },
        }
    ],
    indirect=True,
)
def test_optional_dependencies_version_solving(project):
    # move foo out of the components folder
    shutil.move(
        os.path.join(project, 'components', 'foo'),
        os.path.join(project, 'foo'),
    )

    # reconfigure with esp32
    output = project_action(project, 'set-target', 'esp32', 'reconfigure')
    assert 'Configuring done' in output

    with open(os.path.join(project, 'dependencies.lock')) as fr:
        d = yaml.safe_load(fr)
        assert d['direct_dependencies'] == [
            'example/cmp',
            'foo',
            'idf',
        ]

        assert 'espressif/esp_wrover_kit' in d['dependencies']

    # reconfigure with s3
    output = project_action(project, 'set-target', 'esp32s3', 'reconfigure')
    assert 'Configuring done' in output

    with open(os.path.join(project, 'dependencies.lock')) as fr:
        d = yaml.safe_load(fr)
        assert d['direct_dependencies'] == [
            'example/cmp',
            'foo',
            'idf',
        ]

        assert 'espressif/esp_wrover_kit' not in d['dependencies']


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {'version': '*'},
                        'foo': {'path': '../foo'},
                    }
                },
                'foo': {
                    'dependencies': {
                        'espressif/esp_wrover_kit': {
                            'version': '*',
                            'rules': [
                                {'if': 'target in [esp32]'},
                            ],
                        },
                    }
                },
            },
        }
    ],
    indirect=True,
)
def test_optional_dependencies_unmet_first_then_met(project):
    # move foo out of the components folder
    shutil.move(
        os.path.join(project, 'components', 'foo'),
        os.path.join(project, 'foo'),
    )

    # reconfigure with s3
    output = project_action(project, 'set-target', 'esp32s3', 'reconfigure')
    assert 'Configuring done' in output

    with open(os.path.join(project, 'dependencies.lock')) as fr:
        d = yaml.safe_load(fr)
        assert d['direct_dependencies'] == [
            'example/cmp',
            'foo',
            'idf',
        ]

        assert 'espressif/esp_wrover_kit' not in d['dependencies']

    # reconfigure with esp32
    output = project_action(project, 'set-target', 'esp32', 'reconfigure')
    assert 'Configuring done' in output

    with open(os.path.join(project, 'dependencies.lock')) as fr:
        d = yaml.safe_load(fr)
        assert d['direct_dependencies'] == [
            'example/cmp',
            'foo',
            'idf',
        ]

        assert 'espressif/esp_wrover_kit' in d['dependencies']


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'idf': {
                            'version': '>=4.3',
                        },
                        'espressif/rmaker_common': {
                            'version': '*',
                        },
                    }
                }
            }
        }
    ],
    indirect=True,
)
def test_major_version_changed_with_existing_lock(project, monkeypatch):
    monkeypatch.setenv('IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32s3')

    # lock file is an old version 1.0.0
    with open(os.path.join(project, 'dependencies.lock'), 'w') as fw:
        yaml.dump(
            {
                'dependencies': {
                    'espressif/rmaker_common': {
                        'component_hash': 'ea9a31452ba0f21209376d30f8f97a41c36287cfd729ad400606ad63c62313c5',
                        'version': '1.0.0',
                        'source': {
                            'type': 'service',
                        },
                    },
                    'idf': {
                        'version': '5.4.0',
                        'source': {
                            'type': 'idf',
                        },
                    },
                },
                'manifest_hash': 'a5f45fdb2f073046b6ee07dcc567b37b255a3d302f9646e1e44e16adcef39db3',
                'target': 'esp32s3',
                'version': '1.0.0',
            },
            fw,
        )

    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res
    assert_dependency_version(project, 'espressif/rmaker_common', '1.0.0')


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'idf': {
                            'version': '>=4.3',
                        },
                        'espressif/rmaker_common': {
                            'version': '*',
                        },
                    }
                }
            }
        }
    ],
    indirect=True,
)
def test_major_version_changed_with_incomplete_existing_lock(project, monkeypatch):
    monkeypatch.setenv('IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32s3')

    # lock file is an old version 1.0.0
    with open(os.path.join(project, 'dependencies.lock'), 'w') as fw:
        yaml.dump(
            {
                'dependencies': {
                    'espressif/rmaker_common': {
                        'component_hash': 'ea9a31452ba0f21209376d30f8f97a41c36287cfd729ad400606ad63c62313c5',
                        'version': '1.0.0',
                        'source': {
                            'type': 'service',
                        },
                    },
                    # idf missing
                },
                'manifest_hash': 'a5f45fdb2f073046b6ee07dcc567b37b255a3d302f9646e1e44e16adcef39db3',
                'target': 'esp32s3',
                'version': '1.0.0',
            },
            fw,
        )

    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res

    assert_dependency_version(project, 'espressif/rmaker_common', '1.0.0')
