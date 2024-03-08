# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import typing as t
from abc import ABCMeta, abstractmethod

from schema import Optional

import idf_component_tools as tools
from idf_component_tools.hash_tools.validate_managed_component import (
    validate_managed_component_by_manifest,
)

from ..errors import FetchingError, SourceError
from ..file_cache import FileCache
from ..semver import SimpleSpec

if t.TYPE_CHECKING:
    from ..manifest import ComponentWithVersions, ManifestManager
    from ..manifest.solved_component import SolvedComponent

VALUE_TYPES = {
    'str': str,
    'bool': bool,
}


class BaseSource:
    __metaclass__ = ABCMeta
    NAME = 'base'

    def __init__(
        self,
        source_details: t.Optional[t.Dict] = None,
        system_cache_path: t.Optional[str] = None,
        manifest_manager: t.Optional[ManifestManager] = None,
    ) -> None:
        self._source_details = source_details or {}
        self._hash_key = None

        if system_cache_path is None:
            system_cache_path = FileCache().path()
        self.system_cache_path = system_cache_path

        self.is_overrider = False

        unknown_keys = [key for key in self._source_details.keys() if key not in self.known_keys()]
        if unknown_keys:
            raise SourceError('Unknown keys in dependency details: %s' % ', '.join(unknown_keys))

        self._manifest_manager = manifest_manager

    def _hash_values(self):
        return self.name, self.hash_key

    def cache_path(self) -> str:
        path = os.path.join(self.system_cache_path, f'{self.NAME}_{self.hash_key[:8]}')
        return path

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseSource):
            return NotImplemented

        return self._hash_values() == other._hash_values() and self.name == other.name

    def __hash__(self):
        return hash(self._hash_values())

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self.hash_key})'

    @staticmethod
    def fromdict(
        name: str,
        details: t.Dict,
        manifest_manager: t.Optional[ManifestManager] = None,
    ) -> t.List[BaseSource]:
        """Build component source by dict"""
        for source_class in tools.sources.KNOWN_SOURCES:
            # MARKER
            sources = source_class.build_if_valid(name, details, manifest_manager)

            if sources:
                return sources
            else:
                continue

        raise SourceError(f'Unknown source for component: {name}')

    @staticmethod
    def create_sources_if_valid(
        name: str, details: t.Dict, manifest_manager: t.Optional[ManifestManager] = None
    ) -> t.Union[t.List[BaseSource], None]:
        return None

    @classmethod
    def required_keys(cls):
        return {}

    @classmethod
    def optional_keys(cls):
        return {}

    @classmethod
    def known_keys(cls) -> t.List[str]:
        """List of known details key"""
        return (
            ['version', 'public', 'matches', 'rules', 'require']
            + list(cls.required_keys().keys())
            + list(cls.optional_keys().keys())
        )

    @classmethod
    def schema(cls) -> t.Dict:
        """Schema for lock file"""
        source_schema: t.Dict[str, t.Union[str, t.Callable]] = {'type': cls.NAME}

        for key, type_field in cls.required_keys().items():
            source_schema[key] = VALUE_TYPES[type_field]

        for key, type_field in cls.optional_keys().items():
            source_schema[Optional(key)] = VALUE_TYPES[type_field]

        return source_schema

    @classmethod
    def build_if_valid(cls, name, details, manifest_manager=None):
        """Returns source if details are matched, otherwise returns None"""
        return cls.create_sources_if_valid(name, details, manifest_manager)

    @property
    def source_details(self):
        return self._source_details

    @property
    def name(self):
        return self.NAME

    @property
    def hash_key(self):
        """Hash key is used for comparison sources initialised with different settings"""
        return 'Base'

    @property
    def component_hash_required(self) -> bool:
        """Returns True if component's hash have to present and be validated"""
        return False

    @property
    def downloadable(self) -> bool:
        """Returns True if components have to be fetched"""
        return False

    @property
    def meta(self) -> bool:
        """
        Returns True for meta components.
        Meta components are not included in the build directly
        """
        return False

    @property
    def volatile(self) -> bool:
        """
        Returns True for volatile components.
        Volatile components may change their content, even if their version stays the same.
        """
        return False

    def normalized_name(self, name: str) -> str:
        return name

    def up_to_date(self, component: SolvedComponent, path: str) -> bool:
        if self.component_hash_required and not component.component_hash:
            raise FetchingError('Cannot install component with unknown hash')

        if self.downloadable:
            if not os.path.isdir(path):
                return False

            if component.component_hash:
                return validate_managed_component_by_manifest(path, component.component_hash)

        return True

    def validate_version_spec(self, spec: str) -> bool:
        if not spec or spec == '*':
            return True

        try:
            return bool(SimpleSpec(spec))
        except ValueError:
            return False

    def normalize_spec(self, spec: str) -> str:
        return spec or '*'

    @abstractmethod
    def versions(
        self,
        name: str,
        details: t.Optional[t.Dict] = None,
        spec: str = '*',
        target: t.Optional[str] = None,
    ) -> ComponentWithVersions:
        """List of versions for given spec"""

    @abstractmethod
    def download(self, component: SolvedComponent, download_path: str) -> t.Optional[str]:
        """
        Fetch required component version from the source
        Returns list of absolute paths to directories with component on local filesystem
        """

    @abstractmethod
    def serialize(self) -> t.Dict:
        """
        Return fields to describe source to be saved in lock file
        """
