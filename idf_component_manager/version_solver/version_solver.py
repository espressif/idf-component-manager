# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import os

from idf_component_tools.errors import DependencySolveError, FetchingError, SolverError
from idf_component_tools.lock.manager import EMPTY_LOCK
from idf_component_tools.manifest import (
    ComponentRequirement,
    ComponentWithVersions,
    Manifest,
    ProjectRequirements,
)
from idf_component_tools.manifest.solved_component import SolvedComponent
from idf_component_tools.manifest.solved_manifest import SolvedManifest
from idf_component_tools.registry.api_client_errors import ComponentNotFound
from idf_component_tools.sources import BaseSource, LocalSource

from ..utils import print_info, print_warn
from .helper import PackageSource
from .mixology.failure import SolverFailure
from .mixology.package import Package
from .mixology.version_solver import VersionSolver as Solver

try:
    from typing import Callable
except ImportError:
    pass

logger = logging.getLogger(__name__)


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

        self._init()

    def _init(self):
        # put all the intermediate generated attrs here
        # to reset them when the solver is re-used
        self._source = PackageSource()
        self._solver = Solver(self._source)
        self._target = None
        self._overriders = set()  # type: set[str]
        self._local_root_requirements = dict()  # type: dict[str, ComponentRequirement]
        self._parse_local_root_requirements()

        self._solved_requirements = set()  # type: set[ComponentRequirement]

    def _parse_local_root_requirements(self):  # type: () -> None
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

        # add all local components, except [0] -> main component
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
                    sources=[_source],
                    version_spec=str(manifest.version),
                )

    def _solve(self, cur_solution=None):  # type: (SolvedManifest | None) -> SolvedManifest
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
            kwargs = {'name': package.name, 'source': package.source, 'version': version}
            if package.source.component_hash_required:
                kwargs['component_hash'] = version.component_hash
            if version.targets:
                kwargs['targets'] = version.targets
            solved_components.append(SolvedComponent(**kwargs))  # type: ignore
        return SolvedManifest(
            solved_components, self.requirements.manifest_hash, self.requirements.target
        )

    def solve(self):  # type: () -> SolvedManifest
        if self.old_solution != SolvedManifest.fromdict(EMPTY_LOCK):
            try:
                return self._solve(self.old_solution)
            except SolverFailure as e:
                logger.debug(
                    'Solver failed to solve the requirements with the current solution. '
                    'Error: %s.\n'
                    'Retrying without the current solution. ',
                    e,
                )

        self._init()
        return self._solve()

    def get_versions_from_sources(
        self,
        requirement,  # type: ComponentRequirement
        cur_solution=None,  # type: SolvedManifest | None
    ):  # type: (...) -> tuple[ComponentWithVersions | None, BaseSource | None]
        latest_source = None
        cmp_with_versions = None
        for source in requirement.sources:
            try:
                if cur_solution and requirement.name in cur_solution.solved_components:
                    cmp_with_versions = requirement.source.versions(
                        name=requirement.name,
                        spec=str(cur_solution.solved_components[requirement.name].version),
                        target=self.requirements.target,
                    )
                else:
                    cmp_with_versions = source.versions(
                        name=requirement.name,
                        spec=requirement.version_spec,
                        target=self.requirements.target,
                    )
                latest_source = source
                if cmp_with_versions.versions:
                    break
            # ComponentNotFound will be raised by API client
            # FetchingError will be raised by sources
            except (ComponentNotFound, FetchingError):
                pass
        return cmp_with_versions, latest_source

    def solve_manifest(
        self,
        manifest,  # type: Manifest
        cur_solution=None,  # type: SolvedManifest | None
    ):  # type: (...) -> None
        for dep in self._dependencies_with_local_precedence(
            manifest.dependencies, manifest_path=manifest.path
        ):
            if len(dep.sources) == 1:
                source = dep.source
            else:
                _, source = self.get_versions_from_sources(dep, cur_solution=cur_solution)

            self._source.root_dep(Package(dep.name, source), dep.version_spec)
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
                    'Solver failed processing manifest file "{path}".'
                    '\n{original_error}'.format(path=manifest.path, original_error=str(e))
                )

    def solve_component(
        self, requirement, manifest_path=None, cur_solution=None
    ):  # type: (ComponentRequirement, str | None, SolvedManifest | None) -> None
        if requirement in self._solved_requirements:
            return

        cmp_with_versions, source = self.get_versions_from_sources(
            requirement, cur_solution=cur_solution
        )

        if not cmp_with_versions or not cmp_with_versions.versions or not source:
            print_warn('Component "{}" not found'.format(requirement.name))
            return

        for version in cmp_with_versions.versions:
            if source.is_overrider:
                self._overriders.add(requirement.build_name)

            deps = self._component_dependencies_with_local_precedence(
                version.dependencies, component_name=requirement.name, manifest_path=manifest_path
            )

            self._source.add(
                Package(requirement.name, source),
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

            component_path = self._local_root_requirements[
                matching_dep_name
            ].source._path  # type: ignore

            print_info(
                'Using component placed at {path} '
                'for dependency {dep}{introduced_by}{specified_in}'.format(
                    # must be a local source here
                    path=component_path,
                    dep=dep,
                    introduced_by='(introduced by component {})'.format(component_name)
                    if component_name
                    else '',
                    specified_in=', specified in {}'.format(manifest_path) if manifest_path else '',
                )
            )
            deps.append(self._local_root_requirements[matching_dep_name])

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
