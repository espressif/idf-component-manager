# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os


def getenv_int(name, default):  # type: (str, int) -> int
    '''
    Returns environment variable as an integer, or default if not set.
    Raises ValueError if not an integer.
    '''

    try:
        return int(os.environ.get(name, default))
    except ValueError:
        raise ValueError('Environment variable "{}" must contain a numeric value'.format(name))


def getenv_bool(name, default=False):  # type: (str, bool) -> bool
    '''Returns True if environment variable is set to 1, t, y, yes, true, or False otherwise'''
    return os.getenv(name, str(default)).lower() in {'1', 't', 'true', 'y', 'yes'}
