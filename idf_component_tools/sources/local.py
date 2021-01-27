import os
from typing import Dict

from ..errors import SourceError
from ..manifest import ComponentVersion, ComponentWithVersions, ManifestManager
from .base import BaseSource


class LocalSource(BaseSource):
    NAME = 'local'

    def __init__(self, source_details):
        super(LocalSource, self).__init__(source_details=source_details)

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
        return [self._path]

    def versions(self, name, details=None, spec='*'):
        """For local return version from manifest, or * if manifest not found"""
        manifest_path = os.path.join(self._path, 'idf_component.yml')
        version = ComponentVersion('*')
        if os.path.isfile(manifest_path):
            manifest = ManifestManager(manifest_path).load()
            if manifest.version:
                version = manifest.version
        return ComponentWithVersions(name=name, versions=[version])

    def serialize(self):  # type: () -> Dict
        return {
            'path': self._path,
            'type': self.name,
        }
