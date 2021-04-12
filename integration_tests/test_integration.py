import subprocess

import pytest


def build_project(project_path):
    return subprocess.check_output(['idf.py', '-C', project_path, 'build'])


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'unity': {
                            'git': 'https://github.com/espressif/esp-idf.git',
                            'path': 'components/unity/',
                            'include': 'unity.h'
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
                        'new_component': {
                            'include': 'new_component.h',
                        },
                        'button': {
                            'version': '^1.0.0',
                            'include': 'button.h'
                        }
                    }
                },
                'new_component': {
                    'cmake_lists': {
                        'priv_requires': 'button',
                    },
                }
            },
        }
    ],
    indirect=True)
def test_single_dependency(project):
    build_output = build_project(project)
    assert 'Project build complete.' in str(build_output)
