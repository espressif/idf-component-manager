# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Classes to work with manifest file"""

from __future__ import annotations

import json
import re
import typing as t
from collections import namedtuple
from collections.abc import Mapping
from functools import total_ordering

import idf_component_tools as tools
from idf_component_tools.build_system_tools import build_name, get_env_idf_target
from idf_component_tools.errors import ManifestError
from idf_component_tools.hash_tools.calculate import hash_object
from idf_component_tools.manifest.env_expander import contains_env_variables
from idf_component_tools.messages import notice
from idf_component_tools.semver import Version
from idf_component_tools.serialization import serializable

from .constants import COMMIT_ID_RE, LINKS
from .if_parser import OptionalDependency

if t.TYPE_CHECKING:
    from ..sources import BaseSource
    from . import ManifestManager

# Ignore error with using variable in namedtuple
ComponentLinks = namedtuple('ComponentLinks', LINKS)  # type: ignore


@serializable
class Manifest:
    _serialization_properties = [
        'dependencies',
        'description',
        'files',
        'maintainers',
        'name',
        'targets',
        'tags',
        'version',
        'links',
        'license',
        {'name': 'commit_sha', 'default': None, 'serialize_default': False},
        {'name': 'repository_path', 'default': None, 'serialize_default': False},
    ]

    def __init__(
        self,
        # Dependencies, list of component
        dependencies: t.Optional[t.List[ComponentRequirement]] = None,
        description: t.Optional[str] = None,  # Human-readable description
        maintainers: t.Optional[str] = None,  # List of maintainers
        manifest_hash: t.Optional[str] = None,  # Check-sum of manifest content
        name: t.Optional[str] = None,  # Component name
        targets: t.Optional[t.List[str]] = None,  # List of supported chips
        include_files: t.Optional[t.List[str]] = None,
        exclude_files: t.Optional[t.List[str]] = None,
        version: t.Optional[ComponentVersion] = None,  # Version
        tags: t.Optional[t.List[str]] = None,  # List of tags
        links: t.Optional[ComponentLinks] = None,  # Links of the component
        examples: t.Optional[t.List[t.Dict[str, str]]] = None,  # List of paths to the examples
        license_name: t.Optional[str] = None,  # License of the component
        commit_sha: t.Optional[str] = None,
        repository_path: t.Optional[str] = None,
        # manifest manager who generate this manifest
        manifest_manager: t.Optional[ManifestManager] = None,
    ) -> None:
        self.name = name or ''
        self.version = version
        self.maintainers = maintainers
        self.description = description
        if tags is None:
            tags = []
        self.tags = tags

        if dependencies is None:
            dependencies = []
        self._dependencies = dependencies

        if targets is None:
            targets = []
        self.targets = targets

        if include_files is None:
            include_files = []
        if exclude_files is None:
            exclude_files = []
        self.files = {
            'include': include_files,
            'exclude': exclude_files,
        }

        self._manifest_hash = manifest_hash
        self.links = links
        self.examples = examples
        self.license = license_name
        self.commit_sha = commit_sha
        self.repository_path = repository_path

        self._manifest_manager = manifest_manager

    @classmethod
    def fromdict(
        cls,
        manifest_tree: t.Dict,
        name: str,
        manifest_manager: t.Optional[ManifestManager] = None,
    ) -> Manifest:
        """Coverts manifest dict to manifest object"""
        manifest = cls(
            name=name,
            maintainers=manifest_tree.get('maintainers'),
            tags=manifest_tree.get('tags', []),
            description=manifest_tree.get('description'),
            targets=manifest_tree.get('targets', []),
            include_files=manifest_tree.get('files', {}).get('include'),
            exclude_files=manifest_tree.get('files', {}).get('exclude'),
            examples=manifest_tree.get('examples', []),
            license_name=manifest_tree.get('license'),
            commit_sha=manifest_tree.get('repository_info', {}).get('commit_sha'),
            repository_path=manifest_tree.get('repository_info', {}).get('path'),
            manifest_manager=manifest_manager,
        )

        version = manifest_tree.get('version')
        if version:
            manifest.version = ComponentVersion(version)

        for name, details in manifest_tree.get('dependencies', {}).items():
            if not isinstance(details, Mapping):
                details = {'version': details}

            sources = tools.sources.BaseSource.fromdict(name, details, manifest_manager)
            component = ComponentRequirement(
                name,
                sources=sources,
                version_spec=details.get('version') or '*',
                public=details.get('public'),
                require=details.get('require', None),
            )
            # Optional dependencies, only if manifest_manager not present or environment is expanded
            if not manifest_manager or (manifest_manager and manifest_manager.process_opt_deps):
                if (
                    manifest_manager
                    and not manifest_manager.expand_environment
                    and contains_env_variables(details)
                ):
                    # This error is considered as programmer error, not user error
                    raise ManifestError(
                        'Environment variables are not allowed in '
                        'rules/matches block of this manifest.'
                    )
                component.optional_requirement = OptionalRequirement.fromdict(details)

            manifest._dependencies.append(component)

        links = {link: manifest_tree.get(link, '') for link in LINKS}
        manifest.links = ComponentLinks(**links)

        return manifest

    @property
    def raw_dependencies(self) -> t.List[ComponentRequirement]:
        """Return all dependencies, ignoring rules/matches"""
        return self._dependencies

    @property
    def dependencies(self) -> t.List[ComponentRequirement]:
        """Return dependencies that meet rules/matches"""
        return filter_optional_dependencies(self._dependencies)

    @property
    def manifest_hash(self) -> str:
        if self._manifest_hash:
            return self._manifest_hash

        serialized = self.serialize(serialize_default=False)  # type: ignore
        self._manifest_hash = hash_object(serialized)
        return self._manifest_hash

    @property
    def path(self) -> str:
        return self._manifest_manager.path if self._manifest_manager else ''


@serializable
class OptionalRequirement:
    """
    Stores the list of `matches` and `rules` for the requirement dependency.
    Each rule represented as `OptionalDependency` object.
    """

    _serialization_properties = [
        'matches',
        'rules',
    ]

    def __init__(
        self,
        matches: t.Optional[t.List[OptionalDependency]] = None,
        rules: t.Optional[t.List[OptionalDependency]] = None,
    ) -> None:
        self.matches = matches or []
        self.rules = rules or []

    def version_spec_if_meet_conditions(self, default_version_spec: str) -> t.Optional[str]:
        """
        Return version spec If
        - The first IfClause that is true among all the specified `matches`
          And
        - All the IfClauses that are true among all the specified `rules`

        :return:
            - if the optional dependency matches, return the version spec if specified, else return '*' # noqa
            - else, return None
        """
        if not self.matches and not self.rules:
            return default_version_spec

        res = None

        # ANY of the `matches`
        for optional_dependency in self.matches:
            if optional_dependency.if_clause.bool_value:
                res = optional_dependency.version or default_version_spec
                break

        # must match at least one `matches`
        if self.matches and res is None:
            return None

        # AND all the `rules`
        for optional_dependency in self.rules:
            if optional_dependency.if_clause.bool_value:
                res = optional_dependency.version or res or default_version_spec
            else:
                return None

        return res

    @classmethod
    def fromdict(cls, d: t.Dict) -> OptionalRequirement:
        def _to_optional_dependency(d):
            if isinstance(d, OptionalDependency):
                return d
            elif isinstance(d, dict):
                return OptionalDependency.fromdict(d)

            raise ValueError(f'Invalid optional dependency: {d}, type {type(d)}')

        return cls(
            matches=[_to_optional_dependency(match) for match in d.get('matches', [])],
            rules=[_to_optional_dependency(rule) for rule in d.get('rules', [])],
        )


@serializable
class ComponentRequirement:
    _serialization_properties = [
        'name',
        'public',
        'sources',
        'version_spec',
        'meet_optional_dependencies',
        {'name': 'require', 'default': True, 'serialize_default': False},
    ]

    def __init__(
        self,
        name: str,
        sources: t.List[BaseSource],
        version_spec: str = '*',
        public: t.Optional[bool] = None,
        optional_requirement: t.Optional[OptionalRequirement] = None,
        require: t.Union[str, bool, None] = None,
    ) -> None:
        self._version_spec = version_spec
        self.sources = sources
        self._name = name
        self.public: t.Optional[bool] = None
        if require == 'public' or public:
            self.public = True
        elif public is False or require == 'private':
            self.public = False
        self.optional_requirement = optional_requirement
        self.require = True if require in ['private', 'public', None] else False

    def __hash__(self):
        return hash(json.dumps(self.serialize()))

    def __eq__(self, other):
        if not isinstance(other, ComponentRequirement):
            return NotImplemented

        return self.serialize() == other.serialize()

    @property
    def source(self):
        return self.sources[0]

    @property
    def meta(self):
        return self.source.meta

    @property
    def name(self):
        """
        Full name of the component with the namespace.

        For components from the registry, it contains the namespace, like <namespace>/<name>
        """
        return self.source.normalized_name(self._name)

    @property
    def build_name(self):
        """
        Name of the component with the namespace, but escaped the `/`.

        Usually used for build system, where `/` is not allowed.
        """
        return build_name(self.name)

    @property
    def short_name(self):
        """Name of the component without the namespace"""
        return self.name.rsplit('/', 1)[-1]

    @property
    def version_spec(self):
        if self.optional_requirement:
            version_spec = self.optional_requirement.version_spec_if_meet_conditions(
                self._version_spec
            )
            if version_spec is not None:
                return version_spec

        return self._version_spec

    @property
    def meet_optional_dependencies(self) -> bool:
        if not self.optional_requirement:
            return True

        if (
            self.optional_requirement.version_spec_if_meet_conditions(self._version_spec)
            is not None
        ):
            return True

        notice(f'Skipping optional dependency: {self.name}')
        return False

    def __repr__(self) -> str:
        return 'ComponentRequirement("{}", {}, version_spec="{}", public={})'.format(
            self.name, self.source, self.version_spec, self.public
        )

    def __str__(self) -> str:
        return f'{self.name}({self.version_spec})'


@total_ordering
@serializable(like='str')
class ComponentVersion:
    def __init__(
        self, version_string: str, dependencies: t.Optional[t.List[ComponentRequirement]] = None
    ) -> None:
        """
        version_string - can be `*`, git commit hash (hex, 160 bit) or valid semantic version string
        """

        self._version_string = version_string.strip().lower()
        self._semver = None

        # Setting flags:
        self.is_commit_id = bool(re.match(COMMIT_ID_RE, self._version_string))
        self.is_any = self._version_string == '*'
        self.is_semver = False

        # Checking format
        if not (self.is_any or self.is_commit_id):
            self._semver = Version(self._version_string)
            self.is_semver = True

    def __eq__(self, other):
        if (
            hasattr(self, 'is_semver')
            and hasattr(other, 'is_semver')
            and self.is_semver
            and other.is_semver
        ):
            return self._semver == other._semver
        else:
            return str(self) == str(other)

    def __lt__(self, other):
        if not (self.is_semver and other.is_semver):
            return False  # must be exactly equal for not semver versions (e.g. commit id version)

        return self._semver < other._semver

    def __gt__(self, other):
        if not (self.is_semver and other.is_semver):
            return False  # must be exactly equal for not semver versions (e.g. commit id version)

        return self._semver > other._semver

    def __repr__(self):
        return f'ComponentVersion("{self._version_string}")'

    def __str__(self):
        return self._version_string

    @property
    def semver(self) -> Version:
        if self.is_semver and self._semver:
            return self._semver
        else:
            raise TypeError('Version is not semantic')


class HashedComponentVersion(ComponentVersion):
    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        component_hash = kwargs.pop('component_hash', None)
        dependencies = kwargs.pop('dependencies', []) or []
        targets = kwargs.pop('targets', [])
        all_build_keys_known = kwargs.pop('all_build_keys_known', True)
        super().__init__(*args, **kwargs)

        self.component_hash = component_hash
        self.dependencies = dependencies
        self.targets = targets
        self.all_build_keys_known = all_build_keys_known

    def __hash__(self):
        return hash(self.component_hash) if self.component_hash else hash(str(self))

    @property
    def text(self):
        return str(self)


class ComponentWithVersions:
    def __init__(self, name: str, versions: t.List[HashedComponentVersion]) -> None:
        self.versions = versions
        self.name = name


class ProjectRequirements:
    """Representation of all manifests required by project"""

    def __init__(self, manifests: t.List[Manifest]) -> None:
        self.manifests = manifests
        self._manifest_hash: t.Optional[str] = None
        self._target: t.Optional[str] = None

    @property
    def target(self) -> str:
        if not self._target:
            self._target = get_env_idf_target()
        return self._target

    @property
    def has_dependencies(self) -> bool:
        return any(manifest.dependencies for manifest in self.manifests)

    @property
    def manifest_hash(self) -> str:
        """Lazily calculate requirements hash"""
        if self._manifest_hash:
            return self._manifest_hash

        manifest_hashes = [manifest.manifest_hash for manifest in self.manifests]
        self._manifest_hash = hash_object(manifest_hashes)
        return self._manifest_hash


def filter_optional_dependencies(
    dependencies: t.List[ComponentRequirement],
) -> t.List[ComponentRequirement]:
    return sorted(
        [dep for dep in dependencies if dep.meet_optional_dependencies],
        key=lambda d: d.name,
    )
