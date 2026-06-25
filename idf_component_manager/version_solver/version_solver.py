# SPDX-FileCopyrightText: 2022-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import typing as t
from collections import defaultdict
from contextlib import contextmanager
from copy import deepcopy

from idf_component_tools import debug, notice
from idf_component_tools.debugger import DEBUG_INFO_COLLECTOR, KCONFIG_CONTEXT
from idf_component_tools.errors import DependencySolveError, InternalError, SolverError
from idf_component_tools.manifest import (
    ComponentRequirement,
    Manifest,
    SolvedComponent,
    SolvedManifest,
)
from idf_component_tools.sources import LocalSource
from idf_component_tools.utils import (
    OverrideRule,
    ProjectRequirements,
    canonical_component_name,
)

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
        # to reset them when the solver is reused
        self._source = PackageSource()
        self._solver = Solver(self._source)
        self._target = None
        self._overriders: t.Set[str] = set()
        self._used_override_rules: t.Set[str] = set()
        self._emitted_override_notices: t.Set[str] = set()

        self._local_root_requirements: t.Dict[str, ComponentRequirement] = {}
        self._parse_local_root_requirements()

        self._solved_requirements: t.Set[ComponentRequirement] = set()
        self._candidate_missed_kconfigs: t.Dict[
            t.Tuple[Package, str, t.Optional[str]],
            t.Dict[str, t.Set[ComponentRequirement]],
        ] = {}

    def _parse_local_root_requirements(self) -> None:
        # scan all LocalSource dependencies and add all local components to _local_root_requirements
        # This ensures that when we process dependencies in the second pass,
        # all local components are already available for matching
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

        # First pass: add all local components to _local_root_requirements
        # This ensures that when we process dependencies in the second pass,
        # all local components are already available for matching
        # Add all local components, except [0] -> main component
        for manifest in self.requirements.manifests[1:]:
            if manifest.real_name and manifest.version and manifest.manifest_manager:
                self._local_root_requirements[manifest.real_name] = ComponentRequirement(
                    name=manifest.real_name,
                    path=os.path.dirname(manifest.path),
                    version=str(manifest.version),
                    manifest_manager=manifest.manifest_manager,
                )

        # Second pass: add local components to the solver with their dependencies
        # Now _local_root_requirements is fully populated, so dependencies can be resolved correctly
        for manifest in self.requirements.manifests[1:]:
            # add itself as highest priority component
            if manifest.real_name and manifest.version and manifest.manifest_manager:
                _source = LocalSource(
                    path=os.path.dirname(manifest.path),
                    manifest_manager=manifest.manifest_manager,
                )
                self._source.add(
                    Package(manifest.real_name, _source),
                    str(manifest.version),
                    deps=self._component_dependencies_with_local_precedence(
                        manifest.requirements, manifest.real_name
                    ),
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
        self._commit_selected_candidate_missed_kconfigs(result.decisions)

        # Warn about unused overrides. Each override is registered under a single
        # canonical key (lookups normalize the requirement name), so there is exactly
        # one entry per override and no deduplication is needed.
        for rule in self.requirements.override_rules.values():
            if rule.origin != 'overrides' or rule.name in self._used_override_rules:
                continue
            notice(
                'Override for "{}" was not used - '
                'this component was not found in the dependency graph'.format(rule.reported_name)
            )

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

    def _apply_override_rule(
        self,
        requirement: ComponentRequirement,
    ) -> t.Tuple[ComponentRequirement, t.Optional[OverrideRule]]:
        """Look up a matching override rule for ``requirement`` (no logging side effects).

        Returns the (possibly replaced) requirement and the matched rule, or the original
        requirement and ``None`` when no override applies. Logging is deferred to the
        caller because whether an override actually takes effect depends on local
        component precedence (see ``_dependencies_with_local_precedence``).
        """
        override_rule = self.requirements.override_rules.get(
            canonical_component_name(requirement.name)
        )
        if not override_rule:
            return requirement, None

        self._used_override_rules.add(override_rule.name)
        return override_rule.replacement, override_rule

    def _notice_override_applied(
        self,
        original_name: str,
        override_rule: OverrideRule,
        manifest_path: t.Optional[str],
        component_name: t.Optional[str],
    ) -> None:
        if override_rule.origin != 'overrides' or original_name in self._emitted_override_notices:
            return
        self._emitted_override_notices.add(original_name)

        message = 'Applying override for dependency "{dep}"{suffix}'.format(
            dep=original_name,
            suffix=self._dependency_origin_suffix(component_name, manifest_path),
        )
        if override_rule.reason:
            message = '{}. Reason: {}'.format(message, override_rule.reason)
        notice(message)

    def _notice_override_shadowed(
        self,
        original_name: str,
        local_path: str,
        manifest_path: t.Optional[str],
        component_name: t.Optional[str],
    ) -> None:
        if original_name in self._emitted_override_notices:
            return
        self._emitted_override_notices.add(original_name)

        notice(
            'Override for dependency "{dep}" is ignored because a component placed at {path} '
            'takes precedence. Components in the project "components" directory (and '
            'EXTRA_COMPONENT_DIRS) always override managed dependencies, including overrides'
            '{suffix}'.format(
                dep=original_name,
                path=local_path,
                suffix=self._dependency_origin_suffix(component_name, manifest_path),
            )
        )

    @staticmethod
    def _dependency_origin_suffix(
        component_name: t.Optional[str], manifest_path: t.Optional[str]
    ) -> str:
        """Build the trailing ``(introduced by ...), specified in ...`` message fragment."""
        introduced_by = f' (introduced by component "{component_name}")' if component_name else ''
        specified_in = f', specified in {manifest_path}' if manifest_path else ''
        return f'{introduced_by}{specified_in}'

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

            package = Package(requirement.name, requirement.source)
            with self._collect_candidate_missed_kconfigs(package, version):
                deps_to_solve = self._component_dependency_requirements_with_local_precedence(
                    version.dependencies,
                    component_name=requirement.name,
                    manifest_path=manifest_path,
                )

            deps = {Package(dep.name, dep.source): dep.version_spec for dep in deps_to_solve}

            self._source.add(
                package,
                version,
                deps=deps,
            )

            for dep in deps_to_solve:
                self.solve_component(dep)

        if self.component_solved_callback:
            self.component_solved_callback()

    @staticmethod
    def _candidate_key(package: Package, version: t.Any) -> t.Tuple[Package, str, t.Optional[str]]:
        return package, str(version), getattr(version, 'component_hash', None)

    @contextmanager
    def _collect_candidate_missed_kconfigs(
        self,
        package: Package,
        version: t.Any,
    ) -> t.Generator[None, None, None]:
        kconfig_ctx = KCONFIG_CONTEXT.get()
        missed_keys = kconfig_ctx.missed_keys
        previous_missed_keys = defaultdict(
            set, {key: set(reqs) for key, reqs in missed_keys.items()}
        )

        try:
            yield
        finally:
            new_missed_keys = {
                key: set(reqs) - previous_missed_keys.get(key, set())
                for key, reqs in missed_keys.items()
                if set(reqs) - previous_missed_keys.get(key, set())
            }
            missed_keys.clear()
            missed_keys.update(previous_missed_keys)

            if new_missed_keys:
                candidate_missed_keys = self._candidate_missed_kconfigs.setdefault(
                    self._candidate_key(package, version), {}
                )
                for key, reqs in new_missed_keys.items():
                    candidate_missed_keys.setdefault(key, set()).update(reqs)

    def _commit_selected_candidate_missed_kconfigs(self, decisions: t.Dict[Package, t.Any]) -> None:
        kconfig_ctx = KCONFIG_CONTEXT.get()
        for package, version in decisions.items():
            if package == Package.root():
                continue

            missed_keys = self._candidate_missed_kconfigs.get(
                self._candidate_key(package, version), {}
            )
            for key, reqs in missed_keys.items():
                kconfig_ctx.missed_keys[key].update(reqs)

    def _dependencies_with_local_precedence(
        self,
        dependencies: t.List[ComponentRequirement],
        component_name: t.Optional[str] = None,
        manifest_path: t.Optional[str] = None,
    ) -> t.List[ComponentRequirement]:
        deps: t.List[ComponentRequirement] = []
        for original_dep in dependencies:
            dep, override_rule = self._apply_override_rule(original_dep)

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
                # No local component shadows this edge, so an override (if any) takes effect.
                if override_rule is not None:
                    self._notice_override_applied(
                        original_dep.name, override_rule, manifest_path, component_name
                    )
                deps.append(dep)
                continue

            local_requirement = self._local_root_requirements[matching_dep_name]
            local_source = local_requirement.source
            if not isinstance(local_source, LocalSource):
                raise InternalError(f'Local source is expected, got {local_source}')

            # A component placed in the project "components" directory (or in
            # EXTRA_COMPONENT_DIRS) has the highest priority in the ESP-IDF build system
            # (project_components override project_managed_components). It therefore wins
            # over the Component Manager's resolution, including overrides: an override
            # whose replacement collides with such a local component cannot take effect,
            # so we warn instead of silently (and misleadingly) claiming it was applied.
            if (
                override_rule is not None
                and override_rule.origin == 'overrides'
                and local_source != dep.source
            ):
                self._notice_override_shadowed(
                    original_dep.name,
                    str(local_source.resolved_path),
                    manifest_path,
                    component_name,
                )
            else:
                notice(
                    'Using component placed at {path} for dependency "{dep}"{suffix}'.format(
                        path=local_source.resolved_path,
                        dep=dep.name,
                        suffix=self._dependency_origin_suffix(component_name, manifest_path),
                    )
                )
            deps.append(local_requirement)

        return deps

    def _component_dependency_requirements_with_local_precedence(
        self,
        dependencies: t.List[ComponentRequirement],
        component_name: t.Optional[str] = None,
        manifest_path: t.Optional[str] = None,
    ) -> t.List[ComponentRequirement]:
        # Evaluate each dependency edge's own ``rules``/``matches`` conditions on the
        # ORIGINAL requirement before applying overrides or local precedence. Otherwise
        # an override would discard the original edge's conditions and pull the
        # replacement into the build unconditionally - even on targets where the
        # original (conditional) edge was never active.
        active_dependencies = [dep for dep in dependencies if dep.meet_optional_dependencies]
        return self._dependencies_with_local_precedence(
            active_dependencies,
            component_name,
            manifest_path,
        )

    def _component_dependencies_with_local_precedence(
        self,
        dependencies: t.List[ComponentRequirement],
        component_name: t.Optional[str] = None,
        manifest_path: t.Optional[str] = None,
    ) -> t.Dict[Package, str]:
        return {
            Package(dep.name, dep.source): dep.version_spec
            for dep in self._component_dependency_requirements_with_local_precedence(
                dependencies,
                component_name,
                manifest_path,
            )
        }
