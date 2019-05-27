import os

from component_manager import ComponentVersion, ComponentWithVersions
from component_manager.manifest_pipeline import ManifestParser

from .base import BaseSource
from .errors import SourceError


class LocalSource(BaseSource):
    def __init__(self, source_details, download_path=None):
        super(LocalSource, self).__init__(source_details=source_details, download_path=download_path)

        self._path = source_details.get("path")

        if not os.path.isdir(self._path):
            raise SourceError("Invalid source path, should be a directory: %s" % self._path)

    def name(self):
        return "Local"

    @staticmethod
    def known_keys():
        return ["version", "path"]

    @staticmethod
    def is_me(name, details):
        return bool(details.get("path", None))

    def hash_key(self):
        self.source_details.get("path")

    def unique_path(self, name, details):
        return ""

    def versions(self, name, details):
        """For local return version from manifest, or 0.0.0 if manifest not found"""
        manifest_path = os.path.join(self._path, "idf_component.yml")
        version_string = "0.0.0"
        if os.path.isfile(manifest_path):
            version_string = (ManifestParser(manifest_path).prepare().manifest_tree.get("version", "0.0.0"))

        return ComponentWithVersions(name=name, versions=[ComponentVersion(version_string)])

    def fetch(self, name, details):
        """`details` are ignored by this implementation"""
        return self._path
