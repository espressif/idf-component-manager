from abc import ABCMeta, abstractmethod

from .errors import SourceError


class BaseSource:
    __metaclass__ = ABCMeta

    def __init__(self, source_details):
        unknown_keys = []
        for key in source_details.keys():
            if key not in self.known_keys():
                unknown_keys.append(key)

        if unknown_keys:
            raise SourceError(
                "Unknown keys in component description %s" % ", ".join(unknown_keys)
            )

        self._source_details = source_details

    def _hash_values(self):
        return tuple(self.source_details.get(key, None) for key in self.hash_keys())

    def __eq__(self, other):
        return (
            self._hash_values() == other._hash_values() and self.name() == other.name()
        )

    def __hash__(self):
        return hash((self.name(), self._hash_values()))

    @property
    def source_details(self):
        return self._source_details

    @staticmethod
    @abstractmethod
    def is_me(name, details):
        return False

    @classmethod
    def build_if_me(cls, name, details):
        """Returns source if details are matched, otherwise returns None"""
        return cls(details) if cls.is_me(name, details) else None

    @staticmethod
    @abstractmethod
    def hash_keys():
        return []

    @abstractmethod
    def name(self):
        return "Base"

    @abstractmethod
    def fetch(self, name, details, components_directory):
        """Fetch required component version from the source"""
        pass

    @staticmethod
    def known_keys():
        """List of known details key  """
        return ["version"]
