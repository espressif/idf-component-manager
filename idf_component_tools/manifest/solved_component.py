"""Results of the solver"""

from typing import Iterable, Optional

from idf_component_tools.serialization import serializable

from ..errors import LockError
from ..sources.base import BaseSource


@serializable
class SolvedComponent(object):
    _serialization_properties = [
        'component_hash',
        'name',
        'source',
        'version',
    ]

    def __init__(
            self,
            name,  # type: str
            version,  # type: str
            source,  # type: BaseSource
            component_hash=None,  # type: Optional[str]
            dependencies=None,  # type: Optional[Iterable[SolvedComponent]]
    ):
        # type: (...) -> None
        self.name = name
        self.version = version
        self.source = source
        self.component_hash = component_hash

        if dependencies is None:
            dependencies = []
        self.dependencies = dependencies

    def __str__(self):
        return ('SolvedComponent: %s %s %s' % (self.name, self.version, self.component_hash))

    @classmethod
    def fromdict(cls, details):
        try:
            source_details = dict(details['source'])
            source_name = source_details.pop('type')
            source = BaseSource.fromdict(source_name, source_details)
            return cls(
                name=details['name'],
                version=details['version'],
                source=source,
                component_hash=details.get('component_hash', None))
        except KeyError as e:
            raise LockError(
                'Cannot parse dependencies lock file. Required field %s is not found for component "%s"' %
                (str(e), details['name']))
