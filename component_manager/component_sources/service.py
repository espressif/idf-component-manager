import os
import shutil

from .base import BaseSource
from .errors import SourceError


class ServiceSource(BaseSource):
    @staticmethod
    def known_keys():
        return ["version", "service_url"]

    @staticmethod
    def hash_keys():
        return ["service_url"]

    @staticmethod
    def is_me(name, details):
        return True

    def fetch(self, name, details, components_directory):
        pass
        # TODO
