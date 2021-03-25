import os

from ..errors import FetchingError
from ..manifest import ComponentWithVersions, HashedComponentVersion
from .base import BaseSource

try:
    from typing import Dict
except ImportError:
    pass


class IDFSource(BaseSource):
    NAME = 'idf'

    def __init__(self, source_details):
        super(IDFSource, self).__init__(source_details=source_details)
        self._version = HashedComponentVersion('*')

    @staticmethod
    def is_me(name, details):
        return name == 'idf'

    @property
    def hash_key(self):
        return str(self._version)

    @property
    def meta(self):
        return True

    def normalized_name(self, name):  # type: (str) -> str
        return self.NAME

    def versions(self, name, details=None, spec='*'):
        """Returns current idf version"""

        return ComponentWithVersions(name=name, versions=[self._version])

    def download(self, component, download_path):
        if 'IDF_PATH' not in os.environ:
            FetchingError('Please set IDF_PATH environment variable with a valid path to ESP-IDF')

        return []

    def serialize(self):  # type: () -> Dict
        return {'type': self.name}
