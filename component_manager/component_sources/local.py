import os
import shutil

from .base import BaseSource
from .errors import SourceError


class LocalSource(BaseSource):
    def name(self):
        return "Local"

    @staticmethod
    def known_keys():
        return ["version", "path"]

    @staticmethod
    def hash_keys():
        return ["path"]

    @staticmethod
    def is_me(name, details):
        return bool(details.get("path", None))

    # TODO: add tests
    def fetch(self, name, details, components_directory):
        if not os.path.isdir(self.source_details["path"]):
            raise SourceError(
                "Invalid source. It's only possible to copy component from directory"
            )

        destination = os.path.join(components_directory, name)
        shutil.copytree(details["path"], destination)
