import os

from ..errors import SourceError
from ..manifest import MANIFEST_FILENAME, ComponentWithVersions, HashedComponentVersion, ManifestManager
from . import utils
from .base import BaseSource

try:
    from typing import Dict
except ImportError:
    pass


class LocalSource(BaseSource):
    NAME = 'local'

    def __init__(self, source_details, **kwargs):
        super(LocalSource, self).__init__(source_details=source_details, **kwargs)

        self._path = source_details.get('path')

        if not os.path.isdir(self._path):
            raise SourceError('Invalid source path, should be a directory: %s' % self._path)

    @classmethod
    def required_keys(cls):
        return ['path']

    @staticmethod
    def is_me(name, details):
        return bool(details.get('path', None))

    @property
    def hash_key(self):
        self.source_details.get('path')

    def download(self, component, download_path):
        directory_name = os.path.basename(self._path)
        component_name_with_namespace = self.normalized_name(component.name)
        component_name = component_name_with_namespace.replace('/', '__')
        component_name_without_namespace = component_name.split('__')[1]
        if component_name != directory_name and component_name.split('__')[1] != directory_name:
            print(
                'WARNING:  Component name "{component_name_with_namespace}" '
                'doesn\'t match the directory name "{directory_name}". '
                'ESP-IDF CMake build system uses directory names as names of components, '
                'so different names may break requirements resolution. '
                'To avoid the problem rename the component directory to '
                '"{component_name}" or "{component_name_without_namespace}"'.format(
                    component_name_with_namespace=component_name_with_namespace,
                    directory_name=directory_name,
                    component_name=component_name,
                    component_name_without_namespace=component_name_without_namespace))
        return [self._path]

    def versions(self, name, details=None, spec='*', target=None):
        """For local return version from manifest, or * if manifest not found"""
        manifest_path = os.path.join(self._path, MANIFEST_FILENAME)
        name = os.path.basename(self._path)

        version_str = '*'
        targets = []
        dependencies = []

        if os.path.isfile(manifest_path):
            manifest = ManifestManager(manifest_path, name=name).load()
            if manifest.version:
                version_str = str(manifest.version)

            if manifest.targets:  # only check when exists
                if target and target not in manifest.targets:
                    return ComponentWithVersions(name=name, versions=[])

                targets = manifest.targets

            dependencies = manifest.dependencies

        return ComponentWithVersions(
            name=name, versions=[HashedComponentVersion(version_str, targets=targets, dependencies=dependencies)])

    def serialize(self):  # type: () -> Dict
        return {
            'path': self._path,
            'type': self.name,
        }

    def normalized_name(self, name):
        return utils.normalized_name(name)
