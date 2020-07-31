"""Classes to work with manifest file"""
import re
from functools import total_ordering
from typing import TYPE_CHECKING, List, Union

import idf_component_tools as tools
import semantic_version as semver

from ..errors import ManifestError
from ..hash_tools import hash_object

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

try:
    from semantic_version import SimpleSpec as Spec
except ImportError:
    from semantic_version import Spec

if TYPE_CHECKING:
    from ..sources import BaseSource

COMMIT_ID_RE = re.compile(r'[0-9a-f]{40}')


class Manifest(object):
    def __init__(
            self,
            name=None,  # type: Union[str, None] # Component name
            version=None,  # type: Union[str, ComponentVersion, None] # Version
            maintainers=None,  # type: Union[str, None] # List of maintainers
            dependencies=None,  # type: Union[List[ComponentRequirement], None] # Dependencies, list of component
            description=None,  # description type: Union[str, None] # Human-readable
            download_url=None,  # type: Union[str, None] # Direct url for tarball download
            url=None,  # type: Union[str, None] # Url of the repo
            targets=None,  # type: Union[List[str], None] # List of supported chips
            manifest_hash=None,  # type: Union[str, None] # Check-sum of manifest content
            name_required=False,  # type: bool # Enables component name check
    ):
        # type: (...) -> None

        if not name and name_required:
            raise ManifestError('Name is required for component')

        self.name = str(name) if name else ''
        self.version = version
        self.maintainers = maintainers
        if dependencies is None:
            dependencies = []
        self.dependencies = dependencies
        self.description = description
        self.download_url = download_url
        self.url = url
        self.manifest_hash = manifest_hash
        if targets is None:
            targets = []
        self.targets = targets

    @classmethod
    def from_dict(cls, manifest_tree, name_required=False):  # type: (dict, bool) -> Manifest
        """Coverts manifest dict to manifest object"""
        manifest = cls(
            name=manifest_tree.get('name'),
            maintainers=manifest_tree.get('maintainers'),
            url=manifest_tree.get('url'),
            description=manifest_tree.get('description'),
            targets=manifest_tree.get('targets', []),
            manifest_hash=hash_object(dict(manifest_tree)),
            name_required=name_required)
        version = manifest_tree.get('version')

        if version:
            manifest.version = ComponentVersion(version)

        for name, details in manifest_tree.get('dependencies', {}).items():
            if not isinstance(details, Mapping):
                details = {'version': details}

            source = tools.sources.BaseSource.from_dict(name, details)
            component = ComponentRequirement(name, source, version_spec=details.get('version') or '*')
            manifest.dependencies.append(component)

        return manifest


class ComponentRequirement(object):
    def __init__(
            self,
            name,  # type: str
            source,  # type: BaseSource
            version_spec='*'):
        # type: (...) -> None
        self.version_spec = version_spec
        self.source = source
        self.name = name


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
            self._semver = Spec(spec_string)
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
