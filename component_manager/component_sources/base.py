from abc import ABCMeta, abstractmethod

from .errors import SourceError


class BaseSource:
    __metaclass__ = ABCMeta

    def __init__(self, source_details=None, download_path=None):
        unknown_keys = []
        for key in source_details.keys():
            if key not in self.known_keys():
                unknown_keys.append(key)

        if unknown_keys:
            raise SourceError(
                "Unknown keys in dependency details: %s" % ", ".join(unknown_keys)
            )

        self._source_details = source_details if source_details else {}
        self._hash_key = None
        self.download_path = download_path

    def _hash_values(self):
        return (self.name(), self.hash_key())

    def __eq__(self, other):
        return (
            self._hash_values() == other._hash_values() and self.name() == other.name()
        )

    def __hash__(self):
        return hash((self.name(), self.hash_key()))

    @property
    def source_details(self):
        return self._source_details

    @staticmethod
    def is_me(name, details):
        return False

    @staticmethod
    def known_keys():
        """List of known details key"""
        return ["version"]

    @classmethod
    def build_if_me(cls, name, details):
        """Returns source if details are matched, otherwise returns None"""
        return cls(details) if cls.is_me(name, details) else None

    def name(self):
        return "Base"

    @property
    def hash_key(self):
        return "Base"

    @abstractmethod
    def unique_path(self, name, details):
        """Unique identifier"""
        pass

    @abstractmethod
    def versions(self, name, details):
        """List of versions for given spec"""
        pass

    @abstractmethod
    def fetch(self, name, details):
        """Fetch required component version from the source
        returns absolute path to archive or directory with component """
        pass