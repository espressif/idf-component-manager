"""Results of the solver"""

from collections import OrderedDict
from typing import List, Union

import component_manager
from component_manager.component_sources import BaseSource
from component_manager.manifest import Manifest


class SolvedComponent(object):
    def __init__(
            self,
            name,  # type: str
            version,  # type: str
            source,  # type: BaseSource
            component_hash=None  # type: Union[str,None]
    ):
        # type: (...) -> None
        self.name = name
        self.version = version
        self.source = source
        self.component_hash = component_hash

    def as_ordered_dict(self):  # type: () -> OrderedDict
        component_elements = [
            ("version", str(self.version)),
            ("source", self.source.as_ordered_dict()),
        ]
        if self.component_hash:
            component_elements.append(("component_hash", self.component_hash))

        return OrderedDict(sorted(component_elements, key=lambda e: e[0]))


class SolverResult(object):
    def __init__(self, manifest, solved_components):  # type: (Manifest, List[SolvedComponent]) -> None
        self._manifest = manifest

        solved_components.sort(key=lambda c: c.name)
        self._solved_components = solved_components

    @classmethod
    def load_yaml(cls, manifest, lock):
        # TODO: create SolverResult from YAML
        solved_components = []
        solution = cls(manifest, solved_components)

        return solution

    @property
    def solved_components(self):  # type: () -> List[SolvedComponent]
        return self._solved_components

    @property
    def manifest(self):  # type: () -> Manifest
        return self._manifest

    def as_ordered_dict(self):  # type: () -> OrderedDict
        dependencies = OrderedDict([(c.name, c.as_ordered_dict()) for c in self.solved_components])  # type: OrderedDict
        solution = OrderedDict([
            ("component_manager_version", str(component_manager.version)),
            ("dependencies", dependencies),
            ("manifest_hash", self.manifest.manifest_hash),
        ])

        return solution
