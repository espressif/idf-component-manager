from typing import Dict, List

from .solved_component import SolvedComponent


class SolvedManifest(object):
    def __init__(self, solved_components, manifest_hash):  # type: (List[SolvedComponent], str) -> None
        if solved_components is None:
            solved_components = []
        solved_components.sort(key=lambda c: c.name)
        self.dependencies = solved_components

        self.manifest_hash = manifest_hash

    @classmethod
    def fromdict(cls, lock):  # type: (Dict) -> SolvedManifest
        solved_components = []
        for name, component in lock['dependencies'].items():
            component['name'] = name
            solved_components.append(SolvedComponent.fromdict(component))

        return cls(
            solved_components,
            manifest_hash=lock['manifest_hash'],
        )

    def serialize(self):
        dependencies = {}
        for dependency in self.dependencies:
            dep_dict = dependency.serialize()
            name = dep_dict.pop('name')
            dependencies[name] = dep_dict

        return {
            'manifest_hash': self.manifest_hash,
            'dependencies': dependencies,
        }
