import os

from component_manager import ComponentVersion, ComponentWithVersions
from component_manager.manifest_pipeline import ManifestPipeline

from .base import BaseSource
from .errors import SourceError


class LocalSource(BaseSource):
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
        manifest_path = os.path.join(details["path"], "idf_component.yml")
        version_string = "0.0.0"
        if os.path.isfile(manifest_path):
            version_string = (
                ManifestPipeline(manifest_path)
                .prepare()
                .manifest_tree.get("version", "0.0.0")
            )

        return ComponentWithVersions(
            name=name, versions=[ComponentVersion(version_string)]
        )

    def fetch(self, name, details):
        """`details` are ignored by this implementation"""
        path = self.source_details.get("path", "")
        if not os.path.isdir(path):
            raise SourceError(
                "Invalid source. It's only possible to use component from directory"
            )

        return path
