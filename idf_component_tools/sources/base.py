# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import typing as t
from abc import abstractmethod

from idf_component_tools.file_cache import FileCache
from idf_component_tools.hash_tools.checksums import ChecksumsModel
from idf_component_tools.semver import SimpleSpec
from idf_component_tools.utils import BaseModel, ComponentWithVersions, Literal

if t.TYPE_CHECKING:
    from idf_component_tools.manifest import SolvedComponent


class BaseSource(BaseModel):
    type: Literal['base'] = 'base'  # type: ignore

    _hash_key = None

    def __init__(
        self,
        system_cache_path: t.Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self._hash_key = None

        self._system_cache_path = (
            FileCache().path() if system_cache_path is None else system_cache_path
        )

    @property
    def system_cache_path(self):
        return self._system_cache_path

    def cache_path(self):  # type: () -> str
        path = os.path.join(self._system_cache_path, '{}_{}'.format(self.type, self.hash_key[:8]))
        return path

    def _hash_values(self):
        return self.type, self.hash_key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseSource):
            return NotImplemented

        return self._hash_values() == other._hash_values() and self.name == other.name

    def __hash__(self):
        return hash(self._hash_values())

    def __str__(self) -> str:
        return self.type

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self.hash_key})'

    @property
    def is_overrider(self):
        return False

    @property
    def name(self):
        return self.type

    @property
    def hash_key(self) -> str:
        """Hash key is used for comparison sources initialised with different settings"""
        return self.type

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
        self, name: str, spec: str = '*', target: t.Optional[str] = None
    ) -> ComponentWithVersions:
        """List of versions for given spec"""

    @abstractmethod
    def download(self, component: 'SolvedComponent', download_path: str) -> t.Optional[str]:
        """
        Fetch required component version from the source
        Returns list of absolute paths to directories with component on local filesystem
        """
        return None

    @abstractmethod
    def version_checksums(self, component: 'SolvedComponent') -> t.Optional[ChecksumsModel]:
        pass
