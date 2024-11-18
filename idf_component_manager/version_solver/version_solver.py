# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import typing as t
from copy import deepcopy

from idf_component_tools import debug, notice
from idf_component_tools.debugger import DEBUG_INFO_COLLECTOR
from idf_component_tools.errors import DependencySolveError, InternalError, SolverError
from idf_component_tools.manifest import (
    ComponentRequirement,
    Manifest,
    SolvedComponent,
    SolvedManifest,
)
from idf_component_tools.sources import LocalSource
from idf_component_tools.utils import ProjectRequirements

from .helper import PackageSource
from .mixology.failure import SolverFailure
from .mixology.package import Package
from .mixology.version_solver import VersionSolver as Solver


class VersionSolver:
    """
    The version solver that finds a set of package versions
    satisfies the root package's dependencies.
    """

    def __init__(
        self,
        requirements: ProjectRequirements,
        old_solution: t.Optional[SolvedManifest] = None,
        component_solved_callback: t.Optional[t.Callable[[], None]] = None,
    ) -> None:
        self.requirements = requirements
        self.old_solution = old_solution
        # remove idf from the old solution. always use the current idf version
        if self.old_solution:
            for d in self.old_solution.dependencies:
                if d.name == 'idf':
                    self.old_solution.dependencies.remove(d)

        self.component_solved_callback = component_solved_callback

        self._init()

    def _init(self):
        # put all the intermediate generated attrs here
        # to reset them when the solver is re-used
        self._source = PackageSource()
        self._solver = Solver(self._source)
        self._target = None
        self._overriders: t.Set[str] = set()

        self._local_root_requirements: t.Dict[str, ComponentRequirement] = {}
        self._parse_local_root_requirements()

        self._solved_requirements: t.Set[ComponentRequirement] = set()

    def _parse_local_root_requirements(self) -> None:
        # scan all LocalSource dependencies
        for manifest in self.requirements.manifests:
            for requirement in manifest.requirements:
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

        # add all local components, except [0] -> main component
        for manifest in self.requirements.manifests[1:]:
            # add itself as highest priority component
            if manifest.real_name and manifest.version and manifest._manifest_manager:
                _source = LocalSource(
                    path=os.path.dirname(manifest.path),
                    manifest_manager=manifest._manifest_manager,
                )
                self._source.add(
                    Package(manifest.real_name, _source),
                    str(manifest.version),
                    deps=self._component_dependencies_with_local_precedence(
                        manifest.requirements, manifest.real_name
                    ),
                )

                self._local_root_requirements[manifest.real_name] = ComponentRequirement(
                    name=manifest.real_name,
                    path=os.path.dirname(manifest.path),
                    version=str(manifest.version),
                    manifest_manager=manifest._manifest_manager,
                )

    def _solve(self, cur_solution: t.Optional[SolvedManifest] = None) -> SolvedManifest:
        """
        Solve the version requirements and return the result.

        :param cur_solution: The current solution to be used as a starting point.
        :raises SolverError: If the solver fails to solve the requirements.
        """
        # root local requirements defined in the file system manifest files
        # would have higher priorities
        for manifest in self.requirements.manifests:
            self.solve_manifest(manifest, cur_solution=cur_solution)

        self._source.override_dependencies(self._overriders)

        result = self._solver.solve()

        solved_components = []
        for package, version in result.decisions.items():
            if package == Package.root():
                continue

            kwargs = {
                'name': package.name,
                'source': package.source,
                'version': version.version,
                'dependencies': version.dependencies,
            }
            if package.source.downloadable:
                kwargs['component_hash'] = version.component_hash

            if version.targets:
                kwargs['targets'] = version.targets

            solved_components.append(SolvedComponent.fromdict(kwargs))

        return SolvedManifest.fromdict({
            'direct_dependencies': self.requirements.direct_dep_names or None,
            'dependencies': solved_components,
            'manifest_hash': self.requirements.manifest_hash,
            'target': self.requirements.target,
        })

    def solve(self) -> SolvedManifest:
        """
        Solve the version requirements and return the result.
        """
        if self.old_solution != SolvedManifest():
            try:
                return self._solve(cur_solution=self.old_solution)
            except SolverFailure as e:
                debug(
                    'Solver failed to solve the requirements with the current solution. Error: %s.\n'
                    'Retrying without the current solution. ',
                    e,
                )

        self._init()
        return self._solve()

    def solve_manifest(
        self, manifest: Manifest, cur_solution: t.Optional[SolvedManifest] = None
    ) -> None:
        debugger = DEBUG_INFO_COLLECTOR.get()
        for dep in self._dependencies_with_local_precedence(
            manifest.requirements, manifest_path=manifest.path
        ):
            if not dep.meet_optional_dependencies:
                continue

            debugger.declare_dep(dep.name, introduced_by=manifest.path)

            self._source.root_dep(Package(dep.name, dep.source), dep.version_spec)
            try:
                self.solve_component(dep, manifest_path=manifest.path, cur_solution=cur_solution)
            except DependencySolveError as e:
                raise SolverError(
                    'Solver failed processing dependency "{dependency}" '
                    'from the manifest file "{path}".\n{original_error}'.format(
                        path=manifest.path, dependency=e.dependency, original_error=str(e)
                    )
                )
            except SolverError as e:
                raise SolverError(
                    'Solver failed processing manifest file "{path}".\n{original_error}'.format(
                        path=manifest.path, original_error=str(e)
                    )
                )

    def solve_component(
        self,
        requirement: ComponentRequirement,
        manifest_path: t.Optional[str] = None,
        cur_solution: t.Optional[SolvedManifest] = None,
    ) -> None:
        if requirement in self._solved_requirements:
            return

        solved_components = deepcopy(cur_solution.solved_components) if cur_solution else {}
        # drop the current solution if the source is different from the current one
        if cur_solution and requirement.name in solved_components:
            if solved_components[requirement.name].source != requirement.source:
                solved_components.pop(requirement.name)

        if cur_solution and requirement.name in solved_components:
            # need to get again to get all info from the SolvedComponent
            # version 1.0 lock file does not include all the info
            # like `dependencies`, and `targets`
            cmp_with_versions = requirement.source.versions(
                name=requirement.name,
                spec=solved_components[requirement.name].version,
                target=cur_solution.target,
            )
        else:
            cmp_with_versions = requirement.source.versions(
                name=requirement.name,
                spec=requirement.version_spec,
                target=self.requirements.target,
            )

        self._solved_requirements.add(requirement)

        if not cmp_with_versions or not cmp_with_versions.versions:
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
                    if dep.meet_optional_dependencies:
                        self.solve_component(dep)

        if self.component_solved_callback:
            self.component_solved_callback()

    def _dependencies_with_local_precedence(
        self,
        dependencies: t.List[ComponentRequirement],
        component_name: t.Optional[str] = None,
        manifest_path: t.Optional[str] = None,
    ) -> t.List[ComponentRequirement]:
        deps: t.List[ComponentRequirement] = []
        for dep in dependencies:
            # replace version dependencies to local one if exists
            # use build_name in both recording and replacing
            matching_dep_name = None
            for name in [
                dep.build_name,
                dep.name,
                dep.short_name,
            ]:
                if name in self._local_root_requirements:
                    matching_dep_name = name
                    break

            if not matching_dep_name:
                deps.append(dep)
                continue

            if not isinstance(self._local_root_requirements[matching_dep_name].source, LocalSource):
                raise InternalError(
                    f'Local source is expected, got {self._local_root_requirements[matching_dep_name].source}'
                )

            notice(
                'Using component placed at {path} '
                'for dependency "{dep}"{introduced_by}{specified_in}'.format(
                    # must be a local source here
                    path=self._local_root_requirements[matching_dep_name].source._path,  # type: ignore
                    dep=dep.name,
                    introduced_by='(introduced by component "{}")'.format(component_name)
                    if component_name
                    else '',
                    specified_in=', specified in {}'.format(manifest_path) if manifest_path else '',
                )
            )
            deps.append(self._local_root_requirements[matching_dep_name])

        return deps

    def _component_dependencies_with_local_precedence(
        self,
        dependencies: t.List[ComponentRequirement],
        component_name: t.Optional[str] = None,
        manifest_path: t.Optional[str] = None,
    ) -> t.Dict[Package, str]:
        deps: t.Dict[Package, str] = {}
        for dep in self._dependencies_with_local_precedence(
            dependencies,
            component_name,
            manifest_path,
        ):
            if dep.meet_optional_dependencies:
                deps[Package(dep.name, dep.source)] = dep.version_spec

        return deps
