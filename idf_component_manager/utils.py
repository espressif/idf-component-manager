# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import enum
import sys
from enum import Enum

from idf_component_tools.semver import Version

if sys.version_info < (3, 8):
    import importlib_metadata
else:
    import importlib.metadata as importlib_metadata

CLICK_VERSION = Version.coerce(importlib_metadata.version('click'))
CLICK_SUPPORTS_SHOW_DEFAULT = CLICK_VERSION >= Version('7.1.0')


# total_ordering will raise an error in python 2.7 with enum34
#   ValueError: must define at least one ordering operation: < > <= >=
# The reason is that the `dir()` behavior is different,
# ___eq__, __lt__, __hash__ are not in the dir() result.
# define all six operators here
class ComponentSource(str, enum.Enum):
    # These double-quotes are coming from the build system
    IDF_COMPONENTS = '"idf_components"'
    IDF_MANAGED_COMPONENTS = '"idf_managed_components"'
    PROJECT_MANAGED_COMPONENTS = '"project_managed_components"'
    PROJECT_EXTRA_COMPONENTS = '"project_extra_components"'
    PROJECT_COMPONENTS = '"project_components"'

    # the lower value is, the lower priority it is
    @classmethod
    def order(cls):
        return {
            cls.IDF_COMPONENTS: 0,
            cls.IDF_MANAGED_COMPONENTS: 1,
            cls.PROJECT_MANAGED_COMPONENTS: 2,
            cls.PROJECT_EXTRA_COMPONENTS: 3,
            cls.PROJECT_COMPONENTS: 4,
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
