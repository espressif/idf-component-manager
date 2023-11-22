# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Results of the solver"""

from idf_component_tools.serialization import serializable

from ..constants import IDF_COMPONENT_STORAGE_URL
from ..errors import LockError
from ..manifest import ComponentRequirement, ComponentVersion
from ..sources.base import BaseSource

try:
    from typing import Iterable
except ImportError:
    pass


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
        version,  # type: ComponentVersion
        source,  # type: BaseSource
        component_hash=None,  # type: str | None
        dependencies=None,  # type: Iterable[ComponentRequirement] | None
        targets=None,  # type: list[str] | None
    ):
        # type: (...) -> None
        self.name = name
        self.version = version
        self.source = source
        self.component_hash = component_hash
        self.dependencies = dependencies or []
        self.targets = targets or []

    def __repr__(self):
        return 'SolvedComponent <{}({}) {}>'.format(self.name, self.version, self.component_hash)

    def __str__(self):
        if self.source.name == 'service' and self.source._storage_url != IDF_COMPONENT_STORAGE_URL:
            return '{name} ({version}) from {storage_url}'.format(
                name=self.name,
                version=self.version,
                storage_url=self.source._storage_url,
            )
        else:
            return '{name} ({version})'.format(name=self.name, version=self.version)

    @classmethod
    def fromdict(cls, details):
        try:
            source_details = dict(details['source'])
            source_name = source_details.pop('type')
            if source_name == 'service' and 'storage_url' not in source_details:
                source_details['storage_url'] = IDF_COMPONENT_STORAGE_URL
            source = BaseSource.fromdict(source_name, source_details)[0]
            component_hash = details.get('component_hash', None)
            if source.component_hash_required and not component_hash:
                raise LockError(
                    '"component_hash" is required for component '
                    '"%s" in the "dependencies.lock" file' % details['name']
                )

            return cls(
                name=source.normalized_name(details['name']),
                version=ComponentVersion(details['version']),
                source=source,
                component_hash=component_hash,
            )
        except KeyError as e:
            raise LockError(
                'Cannot parse dependencies lock file. '
                'Required field %s is not found for component "%s"' % (str(e), details['name'])
            )
