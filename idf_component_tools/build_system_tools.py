# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
'''Tools for interaction with IDF build system'''
import os
import re
import subprocess  # nosec
import sys
from pathlib import Path

from idf_component_tools.errors import FetchingError, ProcessingError

from .semver import Version

IDF_VERSION_REGEX = re.compile(r'v(\d\.\d(?:\.\d)?)')

CMAKE_PROJECT_LINE = r'include($ENV{IDF_PATH}/tools/cmake/project.cmake)'


def build_name(name):
    name_parts = name.split('/')
    return '__'.join(name_parts)


def get_env_idf_target():  # type: () -> str
    """
    `IDF_TARGET` should be set automatically while compiling with cmake
    """
    env_idf_target = os.getenv('IDF_TARGET')
    if not env_idf_target:
        raise ProcessingError(
            'IDF_TARGET is not set, should be set by CMake, please check your configuration'
        )
    return env_idf_target


def get_idf_version():
    idf_version = os.getenv('IDF_VERSION')
    if idf_version:
        return idf_version

    idf_py_path = os.path.join(get_idf_path(), 'tools', 'idf.py')
    try:
        idf_version = subprocess.check_output([sys.executable, idf_py_path, '--version'])  # nosec
    except subprocess.CalledProcessError:
        raise FetchingError(
            'Could not get IDF version from calling "idf.py --version".\n'
            'idf.py path: {}'.format(idf_py_path)
        )
    else:
        try:
            string_type = basestring  # type: ignore
        except NameError:
            string_type = str

        if not isinstance(idf_version, string_type):
            idf_version = idf_version.decode('utf-8')

    res = IDF_VERSION_REGEX.findall(idf_version)
    if len(res) == 1:
        return str(Version.coerce(res[0]))
    else:
        raise FetchingError(
            'Could not parse IDF version from calling "idf.py --version".\n'
            'Output: {}'.format(idf_version)
        )


def get_idf_path():  # type: () -> str
    try:
        return os.environ['IDF_PATH']
    except KeyError:
        raise FetchingError('Please set IDF_PATH environment variable with a valid path to ESP-IDF')


def is_component(path):  # type: (Path) -> bool
    '''
    This function is used in the manifest processing to determine,
    if the given path is a component or not.
    If the directory on the path:
        - Does not contain CMakeLists.txt, it is not considered as a component
        (nor a project).
        - Contains idf_component.yml, it is considered as a component, as projects
        do not contain it.
        - Contains CMakeLists.txt and this file contains CMAKE_PROJECT_LINE,
        it is considered as a project, otherwise it is considered as a component.
    Note that this function may be adequate only for the manifest processing.
    '''

    cmakelists_path = path / 'CMakeLists.txt'

    if not cmakelists_path.exists():
        return False

    if (path / 'idf_component.yml').exists():
        return True

    with open((str(cmakelists_path)), 'r') as f:
        for line in f:
            if CMAKE_PROJECT_LINE in line:
                return False

    return True
