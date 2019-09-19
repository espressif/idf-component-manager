"""Classes to work with manifest file"""
import re
from functools import total_ordering
from typing import TYPE_CHECKING, Dict, List, Union

import semantic_version as semver

if TYPE_CHECKING:
    from component_manager.component_sources.base import BaseSource

COMMIT_ID_RE = re.compile(r"[0-9a-f]{40}")


class Manifest(object):
    def __init__(
            self,
            name=None,  # type: Union[str, None]
            version=None,  # type: Union[str, ComponentVersion, None]
            maintainers=None,  # type: Union[str, None]
            dependencies=None,  # type: Union[List[ComponentRequirement], None]
            url=None,  # type: Union[str, None]
            manifest_hash=None  # type: Union[str, None]
    ):
        # type: (...) -> None
        self.name = str(name)
        self.version = version
        self.maintainers = maintainers
        if dependencies is None:
            dependencies = []
        self.dependencies = dependencies
        self.url = url
        self.manifest_hash = manifest_hash


class ComponentRequirement(object):
    def __init__(
            self,
            name,  # type: str
            source,  # type: BaseSource
            version_spec='*',
            source_specific_options=None  # type: Union[Dict,None]
    ):
        # type: (...) -> None
        self.version_spec = version_spec
        self.source = source
        self.name = name
        self.source_specific_options = source_specific_options or {}


@total_ordering
class ComponentVersion(object):
    def __init__(self, version_string, component_hash=None):  # type: (str, Union[str, None]) -> None
        """
        version_string - can be `*`, git commit hash (hex, 160 bit) or valid semantic version string
        """

        self.is_commit_id = bool(COMMIT_ID_RE.match(version_string))
        self.is_any = version_string == '*'
        self.is_semver = False

        if not self.is_commit_id and not self.is_any:
            self._semver = semver.Version(version_string)
            self.is_semver = True

        self._version_string = version_string.strip().lower()
        self.component_hash = component_hash

    def __eq__(self, other):
        if self.component_hash != other.component_hash:
            return False

        if self.is_semver and other.is_semver:
            return self._semver == other._semver
        else:
            return self._version_string == other._version_string

    def __lt__(self, other):
        if not self.is_semver or not other.is_semver:
            raise ValueError('Cannot compare versions of different components')

        return self._semver < other._semver

    def __str__(self):
        return self._version_string


class ComponentSpec(object):
    def __init__(self, spec_string):  # type: (str) -> None
        """
        spec_string - git commit hash (hex, 160 bit) or valid semantic version spec
        """
        self.is_commit_id = bool(COMMIT_ID_RE.match(spec_string))
        self.is_semspec = False

        if not self.is_commit_id:
            self._semver = semver.Spec(spec_string)
            self.is_semspec = True

        self._spec_string = spec_string.strip().lower()

    def match(self, version):  # type: (ComponentVersion) -> bool
        """Check whether a Version satisfies the Spec."""
        if version.is_any:
            return True

        if self.is_commit_id:
            return self._spec_string == str(version)
        else:
            return self._semver.match(version)

    def __str__(self):
        return self._spec_string


class ComponentWithVersions(object):
    def __init__(self, name, versions):
        self.versions = versions
        self.name = name
