# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

import pytest

from .integration_test_helpers import build_project, project_action


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

    assert (
        ('project depends on idf' in res and 'version solving failed.' in res) or
        # idf release v4.4 components/freemodbus depends on idf >= 4.1
        ('project depends on both idf (>=4.1) and idf (<4.1)' in res and 'version  solving failed.' in res))


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
