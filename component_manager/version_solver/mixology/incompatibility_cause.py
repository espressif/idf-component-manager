# Copyright 2019 Espressif Systems (Shanghai) CO LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Contains code taken from "poetry" python package
# https://github.com/sdispater/poetry
# Copyright (c) 2018 Sébastien Eustace
# Originally released under MIT license


class IncompatibilityCause(Exception):
    """
    The reason and Incompatibility's terms are incompatible.
    """


class RootCause(IncompatibilityCause):
    pass


class NoVersionsCause(IncompatibilityCause):
    pass


class DependencyCause(IncompatibilityCause):
    pass


class ConflictCause(IncompatibilityCause):
    """
    The incompatibility was derived from two existing incompatibilities
    during conflict resolution.
    """

    def __init__(self, conflict, other):
        self._conflict = conflict
        self._other = other

    @property
    def conflict(self):
        return self._conflict

    @property
    def other(self):
        return self._other

    def __str__(self):
        return str(self._conflict)


class PythonCause(IncompatibilityCause):
    """
    The incompatibility represents a package's python constraint
    (Python versions) being incompatible
    with the current python version.
    """

    def __init__(self, python_version, root_python_version):
        self._python_version = python_version
        self._root_python_version = root_python_version

    @property
    def python_version(self):
        return self._python_version

    @property
    def root_python_version(self):
        return self._root_python_version


class PlatformCause(IncompatibilityCause):
    """
    The incompatibility represents a package's platform constraint
    (OS most likely) being incompatible with the current platform.
    """

    def __init__(self, platform):
        self._platform = platform

    @property
    def platform(self):
        return self._platform


class PackageNotFoundCause(IncompatibilityCause):
    """
    The incompatibility represents a package that couldn't be found by its
    source.
    """

    def __init__(self, error):
        self._error = error

    @property
    def error(self):
        return self._error
