# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""
This module contains utility functions for working with environment variables.
"""

import os
import typing as t

KNOWN_CI_ENVIRONMENTS = {
    'GITHUB_ACTIONS': 'github-actions',
    'GITLAB_CI': 'gitlab-ci',
    'CIRCLECI': 'circle-ci',
    'TRAVIS': 'travis',
    'JENKINS_URL': 'jenkins',
    'DRONE': 'drone',
    'APPVEYOR': 'appveyor',
    'BITBUCKET_COMMIT': 'bitbucket-pipelines',
    'SEMAPHORE': 'semaphore',
    'TEAMCITY_VERSION': 'teamcity',
    'CI': 'unknown',
}


def getenv_int(name: str, default: int) -> int:
    """
    Returns environment variable as an integer, or default if not set.
    Raises ValueError if not an integer.
    """

    try:
        return int(os.environ.get(name, default))
    except ValueError:
        raise ValueError(f'Environment variable "{name}" must contain a numeric value')


def getenv_bool(name: str, default: bool = False) -> bool:
    """Returns True if environment variable is set to 1, t, y, yes, true, or False otherwise"""

    return os.getenv(name, str(default)).lower() in {'1', 't', 'true', 'y', 'yes'}


def getenv_bool_or_string(name: str, default: t.Union[bool, str] = False) -> t.Union[bool, str]:
    """Returns
    - True if environment variable is set to 1, t, y, yes, true,
    - False if environment variable is set to 0, f, n, no, false
    - or the string value otherwise
    """

    value = os.getenv(name, str(default))
    if value.lower() in {'1', 't', 'true', 'y', 'yes'}:
        return True
    elif value.lower() in {'0', 'f', 'false', 'n', 'no'}:
        return False
    else:
        return value


def detect_ci() -> t.Optional[str]:
    """Returns the name of CI environment if running in a CI environment"""

    for env_var, name in KNOWN_CI_ENVIRONMENTS.items():
        if os.environ.get(env_var):
            return name

    return None
