import logging
import os
import shutil
import subprocess
import sys
from io import open
from pathlib import Path

import pytest

from idf_component_tools.manifest.validator import DEFAULT_KNOWN_TARGETS


def fixtures_path(*args):
    return os.path.join(os.path.dirname(__file__), '..', 'tests', 'fixtures', *args)


def live_print_call(*args, **kwargs):
    default_kwargs = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
    }
    kwargs.update(default_kwargs)
    process = subprocess.Popen(*args, **kwargs)

    try:
        string_type = basestring  # type: ignore
    except NameError:
        string_type = str

    res = ''
    for line in process.stdout:
        if not isinstance(line, string_type):
            line = line.decode('utf-8')
        logging.info(line.rstrip())
        res += line

    return res


def idf_version():
    return live_print_call(['idf.py', '--version'])


def project_action(project_path, *actions):
    return live_print_call(['idf.py', '-C', project_path] + list(actions))


def build_project(project_path):
    return project_action(project_path, 'build')


def set_target(project_path, target):
    return live_print_call(['idf.py', '-C', project_path, 'set-target', target])


def skip_for_idf_versions(*versions):
    current_version = idf_version()
    for version in versions:
        if version in current_version:
            logging.info('Skipping the test for %s', current_version)
            return True

    return False


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'git-only-cmp': {
                            'git': 'https://github.com/espressif/example_components.git',
                            'path': 'git-only-cmp',
                            'include': 'git-only-cmp.h'
                        }
                    }
                }
            }
        }, {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '^3.3.0~0',
                            'include': 'cmp.h'
                        }
                    }
                }
            }
        }, {
            'components': {
                'main': {
                    'dependencies': {
                        'new+compo.nent': {
                            'include': 'new+compo.nent.h',
                        },
                        'example/cmp': {
                            'version': '^3.3.0',
                            'include': 'cmp.h'
                        },
                    }
                },
                'new+compo.nent': {
                    'cmake_lists': {
                        'priv_requires': 'cmp',
                    },
                },
            },
        }
    ],
    indirect=True)
def test_single_dependency(project):
    res = build_project(project)
    assert 'Project build complete.' in res


@pytest.mark.parametrize(
    'project', [
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
    ], indirect=True)
def test_idf_version_dependency_failed(project):
    res = project_action(project, 'reconfigure')
    assert 'project depends on idf' in res
    assert 'version solving failed.' in res


@pytest.mark.parametrize(
    'project', [
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
        },
    ], indirect=True)
def test_idf_version_dependency_passed(project):
    res = build_project(project)
    assert 'Project build complete.' in res


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'idf': {
                            'version': '>=4.1.0',
                        }
                    },
                    'targets': ['esp32s2'],
                }
            },
        },
    ],
    indirect=True)
def test_idf_check_target_fail_manifest(project):
    res = set_target(project, 'esp32')
    assert 'Component "main" does not support target esp32' in res


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '0.0.1',
                        },
                    }
                }
            }
        },
    ], indirect=True)
def test_idf_check_target_fail_dependency(project):
    res = set_target(project, 'esp32')
    assert 'project depends on example/cmp (0.0.1) which doesn\'t match any' in res


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'idf': {
                            'version': '>=4.1.0',
                        },
                        'example/cmp': {
                            'version': '3.3.3',
                        },
                    }
                }
            }
        },
    ],
    indirect=True)
def test_idf_check_target_pass(project):
    res = set_target(project, 'esp32')
    assert 'Build files have been written to:' in res


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '>=3.3.5',
                        }
                    }
                }
            }
        },
    ], indirect=True)
def test_changing_target(project):
    if skip_for_idf_versions('v4.1'):
        return

    lock_path = os.path.join(project, 'dependencies.lock')
    res = set_target(project, 'esp32s2')
    assert 'Building ESP-IDF components for target esp32s2' in res
    with open(lock_path, mode='r', encoding='utf-8') as f:
        assert 'esp32s2' in f.read()
    res = set_target(project, 'esp32')
    assert 'Building ESP-IDF components for target esp32\n' in res
    with open(lock_path, mode='r', encoding='utf-8') as f:
        assert 'esp32\n' in f.read()


@pytest.fixture  # fake fixture since can't specify `indirect` for only one fixture
def result(request):
    return getattr(request, 'param')


@pytest.mark.parametrize(
    'project,result', [
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
            }, [
                'test/circular_dependency_a (1.0.0)',
            ]),
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
                            }
                        }
                    }
                }
            }, [
                'test/diamond_dependency_a (1.0.0)',
                'test/diamond_dependency_b (2.0.0)',
                'test/diamond_dependency_c (3.0.0)',
            ]),
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
                            }
                        }
                    }
                }
            }, [
                'test/partial_satisfy_c (1.0.0)',
                'test/partial_satisfy_y (2.0.0)',
            ]),
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
            }, [
                'test/rollback_sequence_a (2.0.0)',
                'test/rollback_sequence_b (1.0.0)',
                'test/rollback_sequence_c (2.0.0)',
            ]),
    ],
    indirect=True)
def test_version_solver(project, result):
    project_path = os.path.join(os.path.dirname(__file__), 'version_solver_projects', project)
    real_result = project_action(project_path, 'fullclean', 'reconfigure')
    for line in result:
        assert line in real_result


@pytest.mark.parametrize(
    'project, result', [
        (
            {
                'components': {
                    'main': {
                        'dependencies': {
                            'component_foo': {
                                'version': '1.0.0',
                                'path': '../../component_foo',
                            }
                        }
                    },
                    'component_foo': {
                        'version': '1.0.0',
                        'dependencies': {
                            'git-only-cmp': {
                                'version': 'main',
                                'git': 'https://github.com/espressif/example_components.git',
                                'path': 'git-only-cmp',
                            },
                        },
                    },
                }
            }, [
                '[1/4] component_foo',
                '[2/4] example/cmp',
                '[3/4] git-only-cmp',
                '[4/4] idf',
            ]),
    ],
    indirect=True)
def test_version_solver_on_local_components(project, result):
    # need to move to another folder, not under the default `components/`
    os.rename(os.path.join(project, 'components', 'component_foo'), os.path.join(project, '..', 'component_foo'))
    real_result = project_action(project, 'fullclean', 'reconfigure')
    for line in result:
        assert line in real_result


@pytest.mark.parametrize(
    'project, result', [
        (
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
            ['[1/2] espressif/es8311', '[2/2] idf'],
        ),
    ],
    indirect=True)
def test_version_solver_with_caret_and_prerelease(project, result):
    real_result = project_action(project, 'fullclean', 'reconfigure')
    for line in result:
        assert line in real_result


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
                    'dependencies': {
                        'example/cmp': {
                            'version': '>=3.3.5',
                        },
                    }
                }
            }
        },
    ],
    indirect=True)
def test_changes_in_component(project):
    res = project_action(project, 'reconfigure')
    assert 'Build files have been written to' in res

    with open(os.path.join(project, 'managed_components', 'example__cmp', 'README.md'), 'w') as f:
        f.write(u'TEST STRING')
    shutil.rmtree(os.path.join(project, 'build'))
    res = project_action(project, 'reconfigure')

    assert 'in the "managed_components" directory were modified' in res

    shutil.move(
        os.path.join(project, 'managed_components', 'example__cmp'),
        os.path.join(project, 'components', 'example__cmp'))
    res = project_action(project, 'reconfigure')

    assert 'Build files have been written to' in res

    shutil.move(os.path.join(project, 'components', 'example__cmp'), os.path.join(project, 'components', 'cmp'))
    res = project_action(project, 'reconfigure')

    assert 'Build files have been written to' in res


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'cmake_lists': {
                        'requires': 'efuse',
                    },
                    'dependencies': {
                        'cmp': {
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
                            'version': '^3.3.0',
                        }
                    }
                }
            }
        },
    ], indirect=True)
def test_fullclean_managed_components(project):
    project_action(project, 'reconfigure')
    assert Path(project, 'managed_components').is_dir()
    project_action(project, 'fullclean')
    assert not Path(project, 'managed_components').is_dir()
    project_action(project, 'reconfigure')
    component_hash = Path(project, 'managed_components', 'example__cmp', '.component_hash')
    with component_hash.open(mode='wt') as hash_file:
        hash_file.write(u'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
    project_action(project, 'fullclean')
    assert Path(project, 'managed_components', 'example__cmp').is_dir()


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
