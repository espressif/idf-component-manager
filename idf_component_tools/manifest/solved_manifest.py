from typing import Dict, List

from .manifest import Manifest
from .solved_component import SolvedComponent

FORMAT_VERSION = '1.0.0'


class SolvedManifest(object):
    def __init__(self, manifest, solved_components):  # type: (Manifest, List[SolvedComponent]) -> None
        self._manifest = manifest

        solved_components.sort(key=lambda c: c.name)
        self._solved_components = solved_components

    @classmethod
    def fromdict(cls, manifest, lock):  # type: (Manifest, Dict) -> SolvedManifest
        solved_components = [
            SolvedComponent.fromdict(name, component) for name, component in lock['dependencies'].items()
        ]

        return cls(manifest, solved_components)

    @property
    def solved_components(self):  # type: () -> List[SolvedComponent]
        return self._solved_components

    @property
    def manifest(self):  # type: () -> Manifest
        return self._manifest

    def __iter__(self):
        return iter(self.asdict().items())

    def asdict(self):  # type: () -> Dict
        dependencies = dict([(c.name, dict(c)) for c in self.solved_components])
        solution = {
            'version': FORMAT_VERSION,
            'manifest_hash': self.manifest.manifest_hash,
            'dependencies': dependencies,
        }

        return solution
