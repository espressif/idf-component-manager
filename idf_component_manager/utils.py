# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import enum
from enum import Enum

import click

from idf_component_tools.semver import Version

CLICK_SUPPORTS_SHOW_DEFAULT = Version(click.__version__) >= Version('7.1.0')


# total_ordering will raise an error in python 2.7 with enum34
#   ValueError: must define at least one ordering operation: < > <= >=
# The reason is that the `dir()` behavior is different,
# ___eq__, __lt__, __hash__ are not in the dir() result.
# define all six operators here
class ComponentSource(str, enum.Enum):
    # These double-quotes are coming from the build system
    IDF_COMPONENTS = '"idf_components"'
    PROJECT_MANAGED_COMPONENTS = '"project_managed_components"'
    PROJECT_EXTRA_COMPONENTS = '"project_extra_components"'
    PROJECT_COMPONENTS = '"project_components"'

    # the lower value is, the lower priority it is
    @classmethod
    def order(cls):
        return {
            cls.IDF_COMPONENTS: 0,
            cls.PROJECT_MANAGED_COMPONENTS: 1,
            cls.PROJECT_EXTRA_COMPONENTS: 2,
            cls.PROJECT_COMPONENTS: 3,
        }

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return self.value == other.value

    def __ne__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return self.value != other.value

    def __lt__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return self.order()[self] < self.order()[other]

    def __le__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return self < other or self == other

    def __gt__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return not self <= other

    def __ge__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return not self < other


class VersionSolverResolution(str, Enum):
    ALL = 'all'
    LATEST = 'latest'
