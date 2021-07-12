import logging
import subprocess

import pytest


def build_project(project_path):
    process = subprocess.Popen(
        ['idf.py', '-C', project_path, 'build'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    try:
        string_type = basestring  # type: ignore
    except NameError:
        string_type = str

    for line in process.stdout:
        if not isinstance(line, string_type):
            line = line.decode('utf-8')
        logging.info(str(line.rstrip()))

        if 'Project build complete.' in line:
            return True

    return False


@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'unity': {
                            'version': '935deb4082676b42c66b1d1acb8278454bc77410',
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
    assert build_project(project)
