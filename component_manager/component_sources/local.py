import os

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

    def fetch(self, name, details):
        """`details` are ignored by this implementation"""
        path = self.source_details.get("path", "")
        if not os.path.isdir(path):
            raise SourceError(
                "Invalid source. It's only possible to use component from directory"
            )

        return path
