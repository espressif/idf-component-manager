"""Results of the solver"""

from typing import Dict, Union

from ..errors import LockError
from ..sources.base import BaseSource


class SolvedComponent(object):
    def __init__(
            self,
            name,  # type: str
            version,  # type: str
            source,  # type: BaseSource
            component_hash=None,  # type: Union[str,None]
    ):
        # type: (...) -> None
        self.name = name
        self.version = version
        self.source = source
        self.component_hash = component_hash

    def __str__(self):
        return ('SolvedComponent: %s %s %s' % (self.name, self.version, self.component_hash))

    def __iter__(self):
        return iter(self.asdict().items())

    def asdict(self):  # type: () -> Dict
        component_elements = {
            'version': str(self.version),
            'source': dict(self.source),
        }

        if self.component_hash:
            component_elements['component_hash'] = self.component_hash

        return component_elements

    @classmethod
    def fromdict(cls, name, details):
        try:
            # raise Exception(details)
            source_details = dict(details['source'])
            source_name = source_details.pop('type')
            source = BaseSource.fromdict(source_name, source_details)
            return cls(
                name=name,
                version=details['version'],
                source=source,
                component_hash=details.get('component_hash', None))
        except KeyError as e:
            raise LockError(
                'Cannot parse dependencies lock file. Required field %s is not found for component "%s"' %
                (str(e), name))
