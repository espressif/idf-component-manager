import os
from typing import Dict

from ..errors import FetchingError
from ..manifest import ComponentVersion, ComponentWithVersions
from .base import BaseSource


class IDFSource(BaseSource):
    NAME = 'idf'

    def __init__(self, source_details):
        super(IDFSource, self).__init__(source_details=source_details)

        # TODO: Add fetching for idf.versions
        self._version = ComponentVersion('*')

    @staticmethod
    def is_me(name, details):
        return name == 'idf'

    @property
    def hash_key(self):
        return str(self._version)

    def versions(self, name, details=None, spec='*'):
        """Returns current idf version"""

        return ComponentWithVersions(name=name, versions=[self._version])

    def download(self, component, download_path):
        if 'IDF_PATH' not in os.environ:
            FetchingError('Please set IDF_PATH environment variable with a valid path to ESP-IDF')

        return os.environ['IDF_PATH']

    def as_dict(self):  # type: () -> Dict
        return {'type': self.name}
