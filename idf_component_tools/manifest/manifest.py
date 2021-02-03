"""Classes to work with manifest file"""
import re
from functools import total_ordering
from typing import TYPE_CHECKING, List, Optional, Union

import semantic_version as semver

import idf_component_tools as tools
from idf_component_tools.hash_tools import hash_object
from idf_component_tools.serialization import serializable

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


@serializable
class Manifest(object):
    _serialization_properties = [
        'dependencies',
        'description',
        'maintainers',
        'name',
        'targets',
        'url',
        'version',
    ]

    def __init__(
            self,
            dependencies=None,  # type: Optional[List[ComponentRequirement]] # Dependencies, list of component
            description=None,  # description type: Optional[str] # Human-readable
            download_url=None,  # type: Optional[str] # Direct url for tarball download
            maintainers=None,  # type: Optional[str] # List of maintainers
            manifest_hash=None,  # type: Optional[str] # Check-sum of manifest content
            name=None,  # type: Optional[str] # Component name
            targets=None,  # type: Optional[List[str]] # List of supported chips
            url=None,  # type: Optional[str] # Url of the repo
            version=None,  # type: Union[ComponentVersion, None] # Version
    ):
        # type: (...) -> None

        self.name = str(name) if name else ''
        self.version = version
        self.maintainers = maintainers
        if dependencies is None:
            dependencies = []
        self._dependencies = dependencies
        self.description = description
        self.download_url = download_url
        self.url = url
        if targets is None:
            targets = []
        self.targets = targets

        self._manifest_hash = manifest_hash

    @classmethod
    def fromdict(cls, manifest_tree):  # type: (dict) -> Manifest
        """Coverts manifest dict to manifest object"""
        manifest = cls(
            name=manifest_tree.get('name'),
            maintainers=manifest_tree.get('maintainers'),
            url=manifest_tree.get('url'),
            description=manifest_tree.get('description'),
            targets=manifest_tree.get('targets', []))
        version = manifest_tree.get('version')

        if version:
            manifest.version = ComponentVersion(version)

        for name, details in manifest_tree.get('dependencies', {}).items():
            if not isinstance(details, Mapping):
                details = {'version': details}

            source = tools.sources.BaseSource.fromdict(name, details)
            component = ComponentRequirement(
                name,
                source,
                version_spec=details.get('version') or '*',
                public=details.get('public', False),
            )
            manifest._dependencies.append(component)

        return manifest

    @property
    def dependencies(self):
        return sorted(self._dependencies, key=lambda d: d.name)

    @property
    def manifest_hash(self):  # type: () -> str
        if self._manifest_hash:
            return self.manifest_hash

        serialized = self.serialize()  # type: ignore
        return hash_object(serialized)


@serializable
class ComponentRequirement(object):
    _serialization_properties = [
        'name',
        'public',
        'source',
        'version_spec',
    ]

    def __init__(
            self,
            name,  # type: str
            source,  # type: BaseSource
            version_spec='*',  # type: str
            public=False,  # type: bool
    ):
        # type: (...) -> None
        self.version_spec = version_spec
        self.source = source
        self._name = name
        self.public = public

    @property
    def meta(self):
        return self.source.meta

    @property
    def name(self):
        return self.source.normalized_name(self._name)


@total_ordering
@serializable(like='str')
class ComponentVersion(object):
    def __init__(self, version_string, component_hash=None):  # type: (str, Optional[str]) -> None
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


class ProjectRequirements(object):
    '''Representation of all manifests required by project'''
    def __init__(self, manifests):  # type: (List[Manifest]) -> None
        self.manifests = manifests
        self._manifest_hash = None

    @property
    def manifest_hash(self):  # type: () -> str
        '''Lazily calculate requirements hash'''
        if self._manifest_hash:
            return self._manifest_hash

        manifest_hashes = [manifest.manifest_hash for manifest in self.manifests]
        return hash_object(manifest_hashes)