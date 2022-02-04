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
    return live_print_call((['idf.py', '-C', project_path, 'set-target', target]))


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
                        'mag3110': {
                            'version': '^1.0.0',
                            'include': 'mag3110.h'
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
                        'button': {
                            'version': '^1.0.0',
                            'include': 'button.h'
                        },
                    }
                },
                'new+compo.nent': {
                    'cmake_lists': {
                        'priv_requires': 'button',
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
    if 'v4.1' in idf_version():
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

    assert 'directory were modified on the disk since the last run of the CMake' in res

    shutil.move(
        os.path.join(project, 'managed_components', 'example__cmp'),
        os.path.join(project, 'components', 'example__cmp'))
    res = project_action(project, 'reconfigure')

    assert 'Build files have been written to' in res

    shutil.move(os.path.join(project, 'components', 'example__cmp'), os.path.join(project, 'components', 'cmp'))
    res = project_action(project, 'reconfigure')

    assert 'Build files have been written to' in res


def test_known_targets():
    branch = os.getenv('IDF_BRANCH')
    if not branch or branch == 'master':
        idf_path = os.environ['IDF_PATH']
        sys.path.append(os.path.join(idf_path, 'tools'))
        from idf_py_actions.constants import PREVIEW_TARGETS, SUPPORTED_TARGETS
        assert SUPPORTED_TARGETS + PREVIEW_TARGETS == DEFAULT_KNOWN_TARGETS


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'mag3110': {
                            'version': '^1.0.0',
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
    component_hash = Path(project, 'managed_components', 'espressif__mag3110', '.component_hash')
    with component_hash.open(mode='wt') as hash_file:
        hash_file.write(u'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
    project_action(project, 'fullclean')
    assert Path(project, 'managed_components', 'espressif__mag3110').is_dir()
