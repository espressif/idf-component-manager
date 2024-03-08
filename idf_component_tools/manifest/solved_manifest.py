# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

from .solved_component import SolvedComponent


class SolvedManifest:
    def __init__(
        self,
        solved_components: t.Optional[t.List[SolvedComponent]],
        manifest_hash: str,
        target: t.Optional[str] = None,
    ) -> None:
        if solved_components is None:
            solved_components = []
        solved_components.sort(key=lambda c: c.name)
        self.dependencies = solved_components
        self.target = target
        self.manifest_hash = manifest_hash

    @classmethod
    def fromdict(cls, lock: t.Dict) -> SolvedManifest:
        solved_components = []
        for name, component in lock.get('dependencies', {}).items():
            component['name'] = name
            solved_components.append(SolvedComponent.fromdict(component))

        return cls(
            solved_components,
            manifest_hash=lock['manifest_hash'],
            target=lock.get('target'),
        )

    def serialize(self):
        dependencies = {}
        for dependency in self.dependencies:
            dep_dict = dependency.serialize()
            name = dep_dict.pop('name')
            dependencies[name] = dep_dict

        solution = {
            'manifest_hash': self.manifest_hash,
            'target': self.target,
        }

        if dependencies:
            solution['dependencies'] = dependencies

        return solution

    @property
    def solved_components(self) -> t.Dict[str, SolvedComponent]:
        return {cmp.name: cmp for cmp in self.dependencies}
