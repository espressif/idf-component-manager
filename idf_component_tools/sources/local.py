# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import typing as t
from pathlib import Path

from pydantic import model_serializer
from pydantic_core.core_schema import SerializerFunctionWrapHandler

from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.errors import InternalError, SourceError
from idf_component_tools.hash_tools.checksums import ChecksumsModel
from idf_component_tools.manager import ManifestManager
from idf_component_tools.messages import warn
from idf_component_tools.utils import (
    ComponentWithVersions,
    HashedComponentVersion,
    Literal,
    subst_vars_in_str,
)

from ..build_system_tools import build_name_to_namespace_name
from .base import BaseSource

if t.TYPE_CHECKING:
    from idf_component_tools.manifest import SolvedComponent


class ManifestContextError(SourceError):
    pass


class SourcePathError(SourceError):
    pass


class LocalSource(BaseSource):
    type: Literal['local'] = 'local'  # type: ignore
    path: t.Optional[str] = None
    override_path: t.Optional[str] = None

    def __repr__(self) -> str:
        return f'{self.type}({self.path or self.override_path})'

    def model_post_init(self, __context: t.Any) -> None:
        if not self.path and not self.override_path:
            raise SourceError('Either "path" or "override_path" must be specified for local source')

    def normalized_name(self, name):
        return build_name_to_namespace_name(name)

    @model_serializer(mode='wrap')
    def serialize_model(self, handler: SerializerFunctionWrapHandler) -> t.Dict[str, t.Any]:
        # serialize from flat dict to {'name': {...}}
        d = handler(self)

        # only use path in the lock file
        # turn override path into path
        # the dir may not exist
        d['path'] = str(self._get_raw_path())  # type: ignore
        d.pop('override_path', None)

        return d

    @property
    def is_overrider(self) -> bool:
        return bool(self.override_path)

    def _get_raw_path(self) -> Path:
        if self.override_path:
            if self.path:
                warn('Both "path" and "override_path" are set. "override_path" will be used.')
            _raw_path = self.override_path
        elif self.path:
            _raw_path = self.path
        else:
            raise InternalError()

        # expand env var in runtime
        path = Path(subst_vars_in_str(_raw_path))

        if path.is_absolute():
            path = path.resolve()
        elif self._manifest_manager:
            path = (Path(self._manifest_manager.path).parent / path).resolve()
        else:
            raise ManifestContextError(
                "Can't reliably evaluate relative path without context: {}".format(str(path))
            )

        return path

    @property
    def _path(self) -> Path:
        path = self._get_raw_path()

        if self.override_path:
            field_name = 'override_path'
        else:
            field_name = 'path'

        if not path.is_dir():  # for Python > 3.6, where .resolve(strict=False)
            raise SourcePathError(
                f'The "{field_name}" field in the manifest file "{path / MANIFEST_FILENAME}" '
                'does not point to a directory. '
                'You can safely remove this field from the manifest '
                'if this project is an example copied from a component repository. '
                'The dependency will be downloaded from the ESP component registry. '
                'Documentation: '
                'https://docs.espressif.com/projects/idf-component-manager/en/latest/reference/'
                'manifest_file.html#override-path'
            )

        if self.is_overrider and path / 'CMakeLists.txt' not in path.iterdir():
            raise SourcePathError(
                "The override_path you're using is pointing"
                ' to directory "%s" that is not a component.' % str(path)
            )

        return path

    @property
    def hash_key(self) -> str:
        return self.path or self.override_path  # type: ignore

    @property
    def volatile(self) -> bool:
        return True

    def download(self, component: 'SolvedComponent', download_path: str) -> str:  # noqa: ARG002
        directory_name = os.path.basename(str(self._path))
        component_with_namespace = component.name.replace('/', '__')
        namespace_and_component = component.name.split('/')
        component_without_namespace = namespace_and_component[-1]
        if (
            component_without_namespace != directory_name
            and component_with_namespace != directory_name
        ):
            alternative_name = (
                f' or "{component_with_namespace}"' if len(namespace_and_component) == 2 else ''
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
                + f'"{component_without_namespace}"{alternative_name}'
            )
        return str(self._path)

    def versions(self, name, spec='*', target=None):  # noqa: ARG002
        """For local return version from manifest, or * if manifest not found"""
        name = self._path.name

        version_str = '*'
        manifest = ManifestManager(self._path, name).load()
        if manifest.version:
            version_str = str(manifest.version)

        if manifest.targets:  # only check when exists
            if target and target not in manifest.targets:
                return ComponentWithVersions(name=name, versions=[])

        targets = manifest.targets
        dependencies = manifest.raw_requirements

        return ComponentWithVersions(
            name=name,
            versions=[
                HashedComponentVersion(version_str, targets=targets, dependencies=dependencies)
            ],
        )

    def version_checksums(self, component: 'SolvedComponent') -> t.Optional[ChecksumsModel]:  # noqa: ARG002
        return None
