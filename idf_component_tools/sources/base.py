from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Callable, Dict, List, Union

import idf_component_tools as tools
from idf_component_tools.manifest import ComponentWithVersions
from schema import Optional, Or
from six import string_types

from ..errors import SourceError

if TYPE_CHECKING:
    from ..manifest import SolvedComponent


class BaseSource(object):
    __metaclass__ = ABCMeta
    NAME = 'base'

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

    @staticmethod
    def from_dict(name, details):  # type: (str, Dict) -> BaseSource
        '''Build component source by dct'''
        for source_class in tools.sources.KNOWN_SOURCES:
            source = source_class.build_if_me(name, details)

            if source:
                return source
            else:
                continue

        raise SourceError('Unknown source for component: %s' % name)

    @staticmethod
    def is_me(name, details):  # type: (str, Dict) -> bool
        return False

    @classmethod
    def required_keys(cls):
        return []

    @classmethod
    def optional_keys(cls):
        return []

    @classmethod
    def known_keys(cls):  # type: () -> List[str]
        """List of known details key"""
        return ['version'] + cls.required_keys() + cls.optional_keys()

    @classmethod
    def schema(cls):  # type: () -> Dict
        """Schema for lock file"""
        source_schema = {'type': cls.NAME}  # type: Dict[str, Union[str, Callable]]

        for key in cls.required_keys():
            source_schema[key] = Or(*string_types)

        for key in cls.optional_keys():
            source_schema[Optional(key)] = Or(*string_types)

        return source_schema

    @classmethod
    def build_if_me(cls, name, details):
        """Returns source if details are matched, otherwise returns None"""
        return cls(details) if cls.is_me(name, details) else None

    @property
    def source_details(self):
        return self._source_details

    @property
    def name(self):
        return self.NAME

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

    @abstractmethod
    def versions(
            self,
            name,  # type: str
            details,  # type: Union[Dict, None]
            spec='*',  # type: str
    ):
        # type: (...) -> ComponentWithVersions
        """List of versions for given spec"""
        pass

    @abstractmethod
    def download(self, component, download_path):  # type: (SolvedComponent, str) -> str
        """
        Fetch required component version from the source
        Returns absolute path to directory with component on local filesystem
        """

        pass

    def __iter__(self):
        return iter(self.as_dict().items())

    @abstractmethod
    def as_dict(self):  # type: () -> Dict
        """
        Return fields to describe source to be saved in lock file
        """

        pass
