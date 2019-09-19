import os
from collections import OrderedDict

from component_manager.manifest import ComponentVersion, ComponentWithVersions
from component_manager.manifest_pipeline import ManifestParser

from .base import BaseSource
from .errors import SourceError


class LocalSource(BaseSource):
    def __init__(self, source_details):
        super(LocalSource, self).__init__(source_details=source_details)

        self._path = source_details.get('path')

        if not os.path.isdir(self._path):
            raise SourceError('Invalid source path, should be a directory: %s' % self._path)

    @property
    def name(self):
        return 'local'

    @staticmethod
    def known_keys():
        return ['version', 'path']

    @staticmethod
    def is_me(name, details):
        return bool(details.get('path', None))

    @property
    def hash_key(self):
        self.source_details.get('path')

    def download(self, component, download_path):
        return self._path

    def versions(self, name, details=None, spec='*'):
        """For local return version from manifest, or * if manifest not found"""
        manifest_path = os.path.join(self._path, 'idf_component.yml')
        version_string = '*'
        if os.path.isfile(manifest_path):
            version_string = (ManifestParser(manifest_path, component=True).prepare().manifest_tree.get('version', '*'))
        return ComponentWithVersions(name=name, versions=[ComponentVersion(version_string)])

    def as_ordered_dict(self):  # type: () -> OrderedDict
        return OrderedDict([('path', self._path), ('type', self.name)])
