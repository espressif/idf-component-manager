# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Results of the solver"""

from typing import Iterable, List, Optional

from idf_component_tools.serialization import serializable

from ..constants import IDF_COMPONENT_STORAGE_URL
from ..errors import LockError
from ..manifest import ComponentRequirement, ComponentVersion
from ..sources.base import BaseSource


@serializable
class SolvedComponent:
    _serialization_properties = [
        'component_hash',
        'name',
        'source',
        'version',
    ]

    def __init__(
        self,
        name: str,
        version: ComponentVersion,
        source: BaseSource,
        component_hash: Optional[str] = None,
        dependencies: Optional[Iterable[ComponentRequirement]] = None,
        targets: Optional[List[str]] = None,
    ) -> None:
        self.name = name
        self.version = version
        self.source = source
        self.component_hash = component_hash
        self.dependencies = dependencies or []
        self.targets = targets or []

    def __repr__(self):
        return f'SolvedComponent <{self.name}({self.version}) {self.component_hash}>'

    def __str__(self):
        if self.source.name == 'service' and self.source._storage_url != IDF_COMPONENT_STORAGE_URL:
            return f'{self.name} ({self.version}) from {self.source._storage_url}'
        else:
            return f'{self.name} ({self.version})'

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
