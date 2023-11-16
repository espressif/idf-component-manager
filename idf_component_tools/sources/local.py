# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from ..errors import SourceError
from ..manifest import (
    MANIFEST_FILENAME,
    ComponentWithVersions,
    HashedComponentVersion,
    ManifestManager,
)
from ..messages import warn
from .base import BaseSource
from .web_service_keys import WEB_SERVICE_OPTIONAL_KEYS

try:
    from typing import Dict
except ImportError:
    pass


class ManifestContextError(SourceError):
    pass


class SourcePathError(SourceError):
    pass


class LocalSource(BaseSource):
    NAME = 'local'

    def __init__(self, source_details, **kwargs):
        super(LocalSource, self).__init__(source_details=source_details, **kwargs)

        self.is_overrider = 'override_path' in self.source_details
        self._raw_path = Path(
            self.source_details.get('override_path' if self.is_overrider else 'path')
        )

    @property
    def _path(self):  # type: () -> Path
        try:
            if self._manifest_manager:
                path = (Path(self._manifest_manager.path).parent / self._raw_path).resolve()
            elif not self._manifest_manager and self._raw_path.is_absolute():
                path = self._raw_path.resolve()
            else:
                raise ManifestContextError(
                    "Can't reliably evaluate relative path without context: {}".format(
                        str(self._raw_path)
                    )
                )

            if not path.is_dir():  # for Python > 3.6, where .resolve(strict=False)
                raise OSError()

        except OSError:
            raise SourcePathError(
                "The 'override_path' field in the manifest file '{}' "
                'does not point to a directory. You can safely '
                'remove this field from the manifest if this project '
                'is an example copied from a component '
                'repository. The dependency will be downloaded from '
                'the ESP component registry. Documentation: '
                'https://docs.espressif.com/projects/idf-component-manager/en/latest/reference/'
                'manifest_file.html'
                '#override-path'.format(str(self._raw_path / 'idf_component.yml'))
            )

        if self.is_overrider and path / 'CMakeLists.txt' not in path.iterdir():
            raise SourcePathError(
                'The override_path you\'re using is pointing'
                ' to directory "%s" that is not a component.' % str(path)
            )

        return path

    @property
    def component_hash_required(self):  # type: () -> bool
        return False

    @classmethod
    def required_keys(cls):
        return {'path': 'str'}

    @classmethod
    def optional_keys(cls):
        # support `web_service` fields for override_path source changing
        local_keys = {'override_path': 'str'}
        local_keys.update(WEB_SERVICE_OPTIONAL_KEYS)
        return local_keys

    @staticmethod
    def create_sources_if_valid(name, details, manifest_manager=None):
        if details.get('path', None) or 'override_path' in details:
            return [LocalSource(details, manifest_manager=manifest_manager)]
        return None

    @property
    def hash_key(self):
        return self.source_details.get('path')

    @property
    def volatile(self):  # type: () -> bool
        return True

    def download(self, component, download_path):
        directory_name = os.path.basename(str(self._path))
        component_with_namespace = component.name.replace('/', '__')
        namespace_and_component = component.name.split('/')
        component_without_namespace = namespace_and_component[-1]
        if (
            component_without_namespace != directory_name
            and component_with_namespace != directory_name
        ):
            alternative_name = (
                ' or "{}"'.format(component_with_namespace)
                if len(namespace_and_component) == 2
                else ''
            )
            warn(
                'Component name "{component_name}" doesn\'t match the '
                'directory name "{directory_name}".\n'.format(
                    component_name=component.name,
                    directory_name=directory_name,
                )
                + 'ESP-IDF CMake build system uses directory names as names '
                + 'of components, so different names may break '
                + 'requirements resolution. To avoid the problem rename the component directory to '
                + '"{component_without_namespace}"{alternative_name}'.format(
                    component_without_namespace=component_without_namespace,
                    alternative_name=alternative_name,
                )
            )
        return str(self._path)

    def versions(self, name, details=None, spec='*', target=None):
        """For local return version from manifest, or * if manifest not found"""
        manifest_path = self._path / MANIFEST_FILENAME
        name = self._path.name

        version_str = '*'
        targets = []
        dependencies = []

        if manifest_path.is_file():
            manifest = ManifestManager(str(manifest_path), name=name).load()
            if manifest.version:
                version_str = str(manifest.version)

            if manifest.targets:  # only check when exists
                if target and target not in manifest.targets:
                    return ComponentWithVersions(name=name, versions=[])

                targets = manifest.targets

            dependencies = manifest.dependencies

        return ComponentWithVersions(
            name=name,
            versions=[
                HashedComponentVersion(version_str, targets=targets, dependencies=dependencies)
            ],
        )

    def serialize(self):  # type: () -> Dict
        return {
            'path': str(self._path),
            'type': self.name,
        }
