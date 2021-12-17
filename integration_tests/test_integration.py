import logging
import os
import subprocess
from io import open

import pytest


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


def build_project(project_path, fullclean=False):
    args = ['idf.py', '-C', project_path, 'build']
    if fullclean:
        args.append('fullclean')
    return live_print_call(args)


def set_target(project_path, target):
    return live_print_call((['idf.py', '-C', project_path, 'set-target', target]))


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'cmp': {
                            'version': '*',
                            'git': 'https://github.com/espressif/example_components.git',
                            'path': 'cmp',
                            'include': 'cmp.h'
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
    res = build_project(project)
    assert 'Cannot find a satisfying version of the component "idf"' in res


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
    assert 'Cannot find a satisfying version of the component "example/cmp"' in res


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
    res = build_project(project_path, fullclean=True)
    for line in result:
        assert line in res
