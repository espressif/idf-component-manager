from abc import ABCMeta, abstractmethod
from collections import OrderedDict

from .errors import SourceError


class BaseSource(object):
    __metaclass__ = ABCMeta

    def __init__(self, source_details=None):  # type: (dict) -> None
        source_details = source_details or {}
        unknown_keys = []
        for key in source_details.keys():
            if key not in self.known_keys():
                unknown_keys.append(key)

        if unknown_keys:
            raise SourceError('Unknown keys in dependency details: %s' % ', '.join(unknown_keys))

        self._source_details = source_details if source_details else {}
        self._hash_key = None

    def _hash_values(self):
        return (self.name, self.hash_key)

    def __eq__(self, other):
        return (self._hash_values() == other._hash_values() and self.name == other.name)

    def __hash__(self):
        return hash(self._hash_values())

    @property
    def source_details(self):
        return self._source_details

    @staticmethod
    def is_me(name, details):
        return False

    @staticmethod
    def known_keys():
        """List of known details key"""
        return ['version']

    @classmethod
    def build_if_me(cls, name, details):
        """Returns source if details are matched, otherwise returns None"""
        return cls(details) if cls.is_me(name, details) else None

    @property
    def name(self):
        return 'base'

    @property
    def hash_key(self):
        """Hash key is used for comparison sources initialised with different settings"""
        return 'Base'

    @property
    def component_hash_required(self):  # type: () -> bool
        """Returns True if component's hash have to present and be validated"""
        return False

    @property
    def downloadable(self):  # type: () -> bool
        """Returns True if components have to be fetched"""
        return False

    def unique_path(self, name, version):
        """Unique identifier"""
        return ''

    @abstractmethod
    def versions(self, name, spec):
        """List of versions for given spec"""
        pass

    @abstractmethod
    def download(self, name, version, download_path):  # type: (str, str, str) -> str
        """
        Fetch required component version from the source
        Returns absolute path to directory with component on local filesystem
        """

        pass

    @abstractmethod
    def as_ordered_dict(self):  # type: () -> OrderedDict
        """
        Return fields to describe source to be saved in lock file
        """

        pass
