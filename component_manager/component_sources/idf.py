import os
from collections import OrderedDict

from semantic_version import Version

from component_manager import ComponentVersion, ComponentWithVersions

from .base import BaseSource


class IDFSource(BaseSource):
    def __init__(self, source_details):
        super(IDFSource, self).__init__(source_details=source_details)

        # TODO: Add fetching for idf.versions
        self._version = Version("0.0.0")

    @property
    def name(self):
        return "idf"

    @staticmethod
    def known_keys():
        return ["version"]

    @staticmethod
    def is_me(name, details):
        return name == "idf"

    @property
    def hash_key(self):
        return str(self._version)

    def unique_path(self, name, version):
        return ""

    def versions(self, name, spec):
        """Returns current idf version"""

        return ComponentWithVersions(name=name, versions=[ComponentVersion(self._version)])

    def local_path(self, name, version, download_path):
        return os.getenv("IDF_PATH")

    def fetch(self, name, version, download_path):
        return self.local_path(name, version, download_path)

    def as_ordered_dict(self):  # type: () -> OrderedDict
        return OrderedDict([("type", self.name)])