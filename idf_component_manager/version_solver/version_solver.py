# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_tools.errors import DependencySolveError, SolverError
from idf_component_tools.manifest import (
    ComponentRequirement, Manifest, ProjectRequirements, SolvedComponent, SolvedManifest)
from idf_component_tools.sources import LocalSource

from ..utils import print_info
from .helper import PackageSource
from .mixology.package import Package
from .mixology.version_solver import VersionSolver as Solver

try:
    from typing import Callable, Optional
except ImportError:
    pass


class VersionSolver(object):
    """
    The version solver that finds a set of package versions
    satisfies the root package's dependencies.
    """
    def __init__(self, requirements, old_solution=None, component_solved_callback=None):
        # type: (ProjectRequirements, Optional[SolvedManifest], Optional[Callable[[], None]]) -> None
        self.requirements = requirements
        self.old_solution = old_solution
        self.component_solved_callback = component_solved_callback

        self._source = PackageSource()
        self._solver = Solver(self._source)
        self._target = None
        self._overriders = set()  # type: set[str]
        self._local_root_requirements = dict()  # type: dict[str, ComponentRequirement]

    def solve(self):  # type: () -> SolvedManifest
        # scan all root local requirements
        # root local requirements defined in the file system manifest files would have higher priorities
        for manifest in self.requirements.manifests:
            for requirement in manifest.dependencies:  # type: ComponentRequirement
                if isinstance(requirement.source, LocalSource):
                    _recorded_requirement = self._local_root_requirements.get(requirement.name)
                    if _recorded_requirement:
                        # can't specify two different root local source dependencies
                        if _recorded_requirement.source.hash_key != requirement.source.hash_key:
                            raise ValueError('Already defined root local requirement {}'.format(repr(requirement)))
                    else:
                        self._local_root_requirements[requirement.name] = requirement

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
            solved_components.append(SolvedComponent(**kwargs))  # type: ignore
        return SolvedManifest(solved_components, self.requirements.manifest_hash, self.requirements.target)

    def solve_manifest(self, manifest):  # type: (Manifest) -> None
        for requirement in manifest.dependencies:  # type: ComponentRequirement
            # replace root requirement to local one if exists
            if not isinstance(requirement.source, LocalSource) and requirement.name in self._local_root_requirements:
                _requirement = self._local_root_requirements[requirement.name]
                print_info(
                    'replace manifest dependency {} to {}'.format(
                        requirement,
                        self._local_root_requirements[requirement.name],
                    ))
            else:
                _requirement = requirement

            self._source.root_dep(Package(_requirement.name, _requirement.source), _requirement.version_spec)
            try:
                self.solve_component(_requirement)
            except DependencySolveError as e:
                raise SolverError(
                    'Solver failed processing dependency "{dependency}" '
                    'from the manifest file "{path}".\n{original_error}'.format(
                        path=manifest.path, dependency=e.dependency, original_error=str(e)))
            except SolverError as e:
                raise SolverError(
                    'Solver failed processing manifest file "{path}".'
                    '\n{original_error}'.format(path=manifest.path, original_error=str(e)))

    def solve_component(self, requirement):  # type: (ComponentRequirement) -> None
        try:
            cmp_with_versions = requirement.source.versions(
                name=requirement.name, spec=requirement.version_spec, target=self.requirements.target)
        except Exception as e:
            raise DependencySolveError(str(e), dependency=requirement.name)

        for version in cmp_with_versions.versions:
            if requirement.source.is_overrider:
                self._overriders.add(requirement.name)

            deps = {}
            for req in version.dependencies:
                # replace version requirement to local one if exists
                if req.name in self._local_root_requirements:
                    print_info(
                        'replace component {}({}) dependency {} to {}'.format(
                            requirement.name,
                            version.text,
                            req,
                            self._local_root_requirements[req.name],
                        ))
                    _req = self._local_root_requirements[req.name]
                else:
                    _req = req

                deps[Package(_req.name, _req.source)] = _req.version_spec

            self._source.add(
                Package(requirement.name, requirement.source),
                version,
                deps=deps,
            )

            if version.dependencies:
                for dep in version.dependencies:
                    self.solve_component(dep)

        if self.component_solved_callback:
            self.component_solved_callback()
