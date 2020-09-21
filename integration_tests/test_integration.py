import os
import subprocess

import pytest


def build_project(project_path):
    return subprocess.check_output(["idf.py", "-C", project_path, "build"])


@pytest.mark.parametrize(
    "project", [
        {
            "dependencies": {
                "unity": {
                    'git': 'https://github.com/espressif/esp-idf.git',
                    'path': 'components/unity/',
                    'include': 'unity.h'
                }
            }
        },
        {
            "dependencies": {
                "mag3110": {
                    'version': '^1.0.0',
                    'include': 'mag3110.h'
                }
            }
        },
        {
            "dependencies": {
                "unity": {
                    'path': os.environ["IDF_PATH"] + '/components/unity/',
                    'include': 'unity.h'
                }
            }
        }
    ],
    indirect=True)
def test_single_dependency(project):
    build_output = build_project(project)
    assert "Project build complete." in str(build_output)
