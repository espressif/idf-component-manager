"""Results of the solver"""

from collections import OrderedDict
from typing import List

from component_management_tools.builders import SourceBuilder
from component_management_tools.component import SolvedComponent as BaseSolvedComponent
from component_management_tools.manifest import Manifest
from strictyaml import YAML

from .. import version as component_manager_version


class SolvedComponent(BaseSolvedComponent):
    def as_ordered_dict(self):  # type: () -> OrderedDict
        component_elements = [
            ('version', str(self.version)),
            ('source', self.source.as_ordered_dict()),
        ]

        if self.source_specific_options:
            component_elements.append(
                (
                    'source_specific_options',
                    OrderedDict(sorted(self.source_specific_options.items())),
                ))

        if self.component_hash:
            component_elements.append(('component_hash', self.component_hash))

        return OrderedDict(sorted(component_elements, key=lambda e: e[0]))

    @classmethod
    def from_yaml(cls, name, details):
        source_details = dict(details['source'])
        source_name = source_details.pop('type')
        source = SourceBuilder(source_name, source_details)()
        return cls(
            name=name,
            version=details['version'],
            source=source,
            component_hash=details.get('component_hash', None),
            source_specific_options=details.get('source_specific_options', {}))


class SolverResult(object):
    def __init__(self, manifest, solved_components):  # type: (Manifest, List[SolvedComponent]) -> None
        self._manifest = manifest

        solved_components.sort(key=lambda c: c.name)
        self._solved_components = solved_components

    @classmethod
    def from_yaml(cls, manifest, lock):  # type: (Manifest, YAML) -> SolverResult
        solved_components = list(
            [SolvedComponent.from_yaml(name, component) for name, component in lock.data['dependencies'].items()])

        return cls(manifest, solved_components)

    @property
    def solved_components(self):  # type: () -> List[SolvedComponent]
        return self._solved_components

    @property
    def manifest(self):  # type: () -> Manifest
        return self._manifest

    def as_ordered_dict(self):  # type: () -> OrderedDict
        dependencies = OrderedDict([(c.name, c.as_ordered_dict()) for c in self.solved_components])  # type: OrderedDict
        solution = OrderedDict(
            [
                ('component_manager_version', str(component_manager_version)),
                ('dependencies', dependencies),
                ('manifest_hash', self.manifest.manifest_hash),
            ])

        return solution
