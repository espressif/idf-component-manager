import os
from collections import OrderedDict

from ..manifest import ComponentVersion, ComponentWithVersions

from .base import BaseSource


class IDFSource(BaseSource):
    def __init__(self, source_details):
        super(IDFSource, self).__init__(source_details=source_details)

        # TODO: Add fetching for idf.versions
        self._version = ComponentVersion('*')

    @property
    def name(self):
        return 'idf'

    @staticmethod
    def known_keys():
        return ['version']

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
        # TODO: handle cases when IDF_PATH is not set
        return os.environ['IDF_PATH']

    def as_ordered_dict(self):  # type: () -> OrderedDict
        return OrderedDict([('type', self.name)])
