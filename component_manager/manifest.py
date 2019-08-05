"""Classes to work with manifest file"""
import re
from functools import total_ordering
from typing import List, Union

import semantic_version as semver

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
    def __init__(self, name, source, versions=None, version_spec='*'):
        self.version_spec = version_spec
        self.source = source
        self.name = name


@total_ordering
class ComponentVersion(object):
    def __init__(self, version_string):  # type: (str) -> None
        """
        version_string - can be `*`, git commit hash (hex, 160 bit) or valid semantic version string
        """
        self.is_commit_id = bool(COMMIT_ID_RE.match(version_string))
        self.is_any = version_string == '*'
        self.is_semver = False

        if not self.is_commit_id and not self.is_any:
            self._semver = semver.Version(version_string)
            self.is_semver = True

        self._version_string = version_string

    def __eq__(self, other):
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


class ComponentWithVersions(object):
    def __init__(self, name, versions):
        self.versions = versions
        self.name = name
