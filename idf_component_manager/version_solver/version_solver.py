# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os

from idf_component_tools.errors import DependencySolveError, SolverError
from idf_component_tools.manifest import (
    ComponentRequirement,
    Manifest,
    ProjectRequirements,
    SolvedComponent,
    SolvedManifest,
)
from idf_component_tools.sources import LocalSource

from ..utils import print_info, print_warn
from .helper import PackageSource
from .mixology.package import Package
from .mixology.version_solver import VersionSolver as Solver

try:
    from typing import Callable
except ImportError:
    pass


class VersionSolver(object):
    """
    The version solver that finds a set of package versions
    satisfies the root package's dependencies.
    """

    def __init__(self, requirements, old_solution=None, component_solved_callback=None):
        # type:(ProjectRequirements, SolvedManifest | None, Callable[[], None] | None) -> None
        self.requirements = requirements
        self.old_solution = old_solution
        self.component_solved_callback = component_solved_callback

        self._source = PackageSource()
        self._solver = Solver(self._source)
        self._target = None
        self._overriders = set()  # type: set[str]
        self._local_root_requirements = dict()  # type: dict[str, ComponentRequirement]
        self._solved_requirements = set()  # type: set[ComponentRequirement]

    def solve(self):  # type: () -> SolvedManifest
        # scan all root local requirements
        # root local requirements defined in the file system manifest files
        # would have higher priorities

        # scan all root local requirements
        for manifest in self.requirements.manifests:
            for requirement in manifest.dependencies:  # type: ComponentRequirement
                if isinstance(requirement.source, LocalSource):
                    _recorded_requirement = self._local_root_requirements.get(
                        requirement.build_name
                    )
                    if _recorded_requirement:
                        # can't specify two different root local source dependencies
                        if _recorded_requirement.source.hash_key != requirement.source.hash_key:
                            raise ValueError(
                                'Already defined root local requirement {}'.format(
                                    repr(requirement)
                                )
                            )
                    else:
                        self._local_root_requirements[requirement.build_name] = requirement

        # scan all root local components
        for manifest in self.requirements.manifests[1:]:
            # add itself as highest priority component
            if manifest.name and manifest.version and manifest._manifest_manager:
                _source = LocalSource({'path': os.path.dirname(manifest._manifest_manager.path)})
                self._source.add(
                    Package(manifest.name, _source),
                    str(manifest.version),
                    deps=self._component_dependencies_with_local_precedence(
                        manifest.dependencies, manifest.name
                    ),
                )

                self._local_root_requirements[manifest.name] = ComponentRequirement(
                    name=manifest.name,
                    source=_source,
                    version_spec=str(manifest.version),
                )

        for manifest in self.requirements.manifests:
            self.solve_manifest(manifest)

        self._source.override_dependencies(self._overriders)

        result = self._solver.solve()

        solved_components = []
        for package, version in result.decisions.items():
            if package == Package.root():
                continue
            kwargs = {'name': package.name, 'source': package.source, 'version': version}
            if package.source.component_hash_required:
                kwargs['component_hash'] = version.component_hash
            if version.targets:
                kwargs['targets'] = version.targets
            solved_components.append(SolvedComponent(**kwargs))  # type: ignore
        return SolvedManifest(
            solved_components, self.requirements.manifest_hash, self.requirements.target
        )

    def solve_manifest(self, manifest):  # type: (Manifest) -> None
        for dep in self._dependencies_with_local_precedence(
            manifest.dependencies, manifest_path=manifest.path
        ):
            self._source.root_dep(Package(dep.name, dep.source), dep.version_spec)
            try:
                self.solve_component(dep, manifest_path=manifest.path)
            except DependencySolveError as e:
                raise SolverError(
                    'Solver failed processing dependency "{dependency}" '
                    'from the manifest file "{path}".\n{original_error}'.format(
                        path=manifest.path, dependency=e.dependency, original_error=str(e)
                    )
                )
            except SolverError as e:
                raise SolverError(
                    'Solver failed processing manifest file "{path}".'
                    '\n{original_error}'.format(path=manifest.path, original_error=str(e))
                )

    def solve_component(
        self, requirement, manifest_path=None
    ):  # type: (ComponentRequirement, str | None) -> None
        if requirement in self._solved_requirements:
            return

        try:
            cmp_with_versions = requirement.source.versions(
                name=requirement.name,
                spec=requirement.version_spec,
                target=self.requirements.target,
            )
        except Exception as e:
            print_warn(e)
            return

        for version in cmp_with_versions.versions:
            if requirement.source.is_overrider:
                self._overriders.add(requirement.build_name)

            deps = self._component_dependencies_with_local_precedence(
                version.dependencies, component_name=requirement.name, manifest_path=manifest_path
            )

            self._source.add(
                Package(requirement.name, requirement.source),
                version,
                deps=deps,
            )

            if version.dependencies:
                for dep in version.dependencies:
                    self.solve_component(dep)

        self._solved_requirements.add(requirement)

        if self.component_solved_callback:
            self.component_solved_callback()

    def _dependencies_with_local_precedence(
        self,
        dependencies,  # type: list[ComponentRequirement]
        component_name=None,  # type: str | None
        manifest_path=None,  # type: str | None
    ):  # type: (...) -> list[ComponentRequirement]
        deps = []  # type: list[ComponentRequirement]
        for dep in dependencies:
            # replace version dependencies to local one if exists
            # use build_name in both recording and replacing
            if dep.build_name in self._local_root_requirements:
                print_info(
                    'Using component placed at {} for dependency {}{}{}'.format(
                        # must be a local source here
                        self._local_root_requirements[dep.build_name].source._path,  # type: ignore
                        dep,
                        '(introduced by component {})'.format(component_name)
                        if component_name
                        else '',
                        ', specified in {}'.format(manifest_path) if manifest_path else '',
                    )
                )
                deps.append(self._local_root_requirements[dep.build_name])
            else:
                deps.append(dep)

        return deps

    def _component_dependencies_with_local_precedence(
        self,
        dependencies,  # type: list[ComponentRequirement]
        component_name=None,  # type: str | None
        manifest_path=None,  # type: str | None
    ):  # type: (...) -> dict[Package, str]
        deps = {}  # type: dict[Package, str]
        for dep in self._dependencies_with_local_precedence(
            dependencies,
            component_name,
            manifest_path,
        ):
            deps[Package(dep.name, dep.source)] = dep.version_spec

        return deps
