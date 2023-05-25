# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
from abc import ABCMeta, abstractmethod

from schema import Optional, Or
from six import string_types

import idf_component_tools as tools

from ..errors import FetchingError, SourceError
from ..file_cache import FileCache
from ..hash_tools import validate_filtered_dir
from ..semver import SimpleSpec

try:
    from typing import TYPE_CHECKING, Callable

    if TYPE_CHECKING:
        from ..manifest import ComponentWithVersions, ManifestManager, SolvedComponent
except ImportError:
    pass

VALUE_TYPES = {
    'str': Or(*string_types),
    'bool': bool,
}


class BaseSource(object):
    __metaclass__ = ABCMeta
    NAME = 'base'

    def __init__(
            self,
            source_details=None,  # type: dict | None
            system_cache_path=None,  # type: str | None
            manifest_manager=None,  # type: ManifestManager | None
    ):  # type: (...) -> None
        self._source_details = source_details or {}
        self._hash_key = None

        if system_cache_path is None:
            system_cache_path = FileCache.path()
        self.system_cache_path = system_cache_path

        self.is_overrider = False

        unknown_keys = [key for key in self._source_details.keys() if key not in self.known_keys()]
        if unknown_keys:
            raise SourceError('Unknown keys in dependency details: %s' % ', '.join(unknown_keys))

        self._manifest_manager = manifest_manager

    def _hash_values(self):
        return self.name, self.hash_key

    def cache_path(self):  # type: () -> str
        path = os.path.join(self.system_cache_path, '{}_{}'.format(self.NAME, self.hash_key[:8]))
        return path

    def __eq__(self, other):  # type: (object) -> bool
        if not isinstance(other, BaseSource):
            return NotImplemented

        return self._hash_values() == other._hash_values() and self.name == other.name

    def __hash__(self):
        return hash(self._hash_values())

    def __repr__(self):  # type: () -> str
        return '{}({})'.format(type(self).__name__, self.hash_key)

    @staticmethod
    def fromdict(
            name,  # type: str
            details,  # type: dict
            manifest_manager=None,  # type: ManifestManager | None
    ):  # type: (...) -> BaseSource
        """Build component source by dict"""
        for source_class in tools.sources.KNOWN_SOURCES:
            # MARKER
            source = source_class.build_if_me(name, details, manifest_manager)

            if source:
                return source
            else:
                continue

        raise SourceError('Unknown source for component: %s' % name)

    @staticmethod
    def is_me(name, details):  # type: (str, dict) -> bool
        return False

    @classmethod
    def required_keys(cls):
        return {}

    @classmethod
    def optional_keys(cls):
        return {}

    @classmethod
    def known_keys(cls):  # type: () -> list[str]
        """List of known details key"""
        return ['version', 'public', 'rules', 'require'] + list(cls.required_keys().keys()) + list(
            cls.optional_keys().keys())

    @classmethod
    def schema(cls):  # type: () -> dict
        """Schema for lock file"""
        source_schema = {'type': cls.NAME}  # type: dict[str, str | Callable]

        for key, type_field in cls.required_keys().items():
            source_schema[key] = VALUE_TYPES[type_field]

        for key, type_field in cls.optional_keys().items():
            source_schema[Optional(key)] = VALUE_TYPES[type_field]

        return source_schema

    @classmethod
    def build_if_me(cls, name, details, manifest_manager=None):
        """Returns source if details are matched, otherwise returns None"""
        return cls(details, manifest_manager=manifest_manager) if cls.is_me(name, details) else None

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
    def component_hash_required(self):  # type: () -> bool
        """Returns True if component's hash have to present and be validated"""
        return False

    @property
    def downloadable(self):  # type: () -> bool
        """Returns True if components have to be fetched"""
        return False

    @property
    def meta(self):  # type: () -> bool
        """Returns True for meta components. Meta components are not included in the build directly"""
        return False

    def normalized_name(self, name):  # type: (str) -> str
        return name

    def up_to_date(self, component, path):  # type: (SolvedComponent, str) -> bool
        if self.component_hash_required and not component.component_hash:
            raise FetchingError('Cannot install component with unknown hash')

        if self.downloadable:
            if not os.path.isdir(path):
                return False

            if component.component_hash:
                return validate_filtered_dir(path, component.component_hash)

        return True

    def validate_version_spec(self, spec):  # type: (str) -> bool
        if not spec or spec == '*':
            return True

        try:
            return bool(SimpleSpec(spec))
        except ValueError:
            return False

    def normalize_spec(self, spec):  # type: (str) -> str
        return spec or '*'

    @abstractmethod
    def versions(
            self,
            name,  # type: str
            details=None,  # type: dict | None
            spec='*',  # type: str
            target=None,  # type: str | None
    ):
        # type: (...) -> ComponentWithVersions
        """List of versions for given spec"""

    @abstractmethod
    def download(self, component, download_path):  # type: (SolvedComponent, str) -> str | None
        """
        Fetch required component version from the source
        Returns list of absolute paths to directories with component on local filesystem
        """

    @abstractmethod
    def serialize(self):  # type: () -> dict
        """
        Return fields to describe source to be saved in lock file
        """
