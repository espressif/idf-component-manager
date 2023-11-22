# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
from functools import total_ordering
from pathlib import Path

from idf_component_manager.core_utils import raise_component_modified_error
from idf_component_manager.utils import print_info, print_warn
from idf_component_manager.version_solver.helper import parse_root_dep_conflict_constraints
from idf_component_manager.version_solver.mixology.failure import SolverFailure
from idf_component_manager.version_solver.mixology.package import Package
from idf_component_manager.version_solver.version_solver import VersionSolver
from idf_component_tools.build_system_tools import build_name
from idf_component_tools.environment import getenv_bool
from idf_component_tools.errors import (
    ComponentModifiedError,
    FetchingError,
    InvalidComponentHashError,
    SolverError,
)
from idf_component_tools.hash_tools.errors import ValidatingHashError
from idf_component_tools.hash_tools.validate_managed_component import (
    validate_managed_component_hash,
)
from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import ProjectRequirements
from idf_component_tools.manifest.solved_component import SolvedComponent
from idf_component_tools.manifest.solved_manifest import SolvedManifest
from idf_component_tools.messages import hint, warn
from idf_component_tools.registry.api_client_errors import NetworkConnectionError
from idf_component_tools.sources.fetcher import ComponentFetcher


def check_manifests_targets(project_requirements):  # type: (ProjectRequirements) -> None
    for manifest in project_requirements.manifests:
        if not manifest.targets:
            continue

        if project_requirements.target not in manifest.targets:
            raise FetchingError(
                'Component "{}" does not support target {}'.format(
                    manifest.name, project_requirements.target
                )
            )


def get_unused_components(
    unused_files_with_components, managed_components_path
):  # type: (set[str], str) -> set[str]
    unused_components = set()

    for component in unused_files_with_components:
        try:
            validate_managed_component_hash(os.path.join(managed_components_path, component))
            unused_components.add(component)
        except ValidatingHashError:
            pass

    return unused_components


def detect_unused_components(
    requirement_dependencies, managed_components_path
):  # type: (list[SolvedComponent], str) -> None
    downloaded_components = os.listdir(managed_components_path)
    unused_files_with_components = set(downloaded_components) - {
        build_name(component.name) for component in requirement_dependencies
    }
    unused_components = get_unused_components(unused_files_with_components, managed_components_path)
    unused_files = unused_files_with_components - unused_components
    if unused_components:
        print_info('Deleting {} unused components'.format(len(unused_components)))
        for unused_component_name in unused_components:
            print_info(' {}'.format(unused_component_name))
            shutil.rmtree(os.path.join(managed_components_path, unused_component_name))
    if unused_files and not getenv_bool('IGNORE_UNKNOWN_FILES_FOR_MANAGED_COMPONENTS'):
        warning = (
            '{} unexpected files and directories were found in the "managed_components" directory:'
        )
        warning = warning.format(len(unused_files))

        for unexpected_name in unused_files:
            warning += ' {}'.format(unexpected_name)

        warning += (
            '\nContent of the managed components directory is managed automatically '
            'and it\'s not recommended to place any files there manually. '
            'To suppress this warning set the environment variable: '
            'IGNORE_UNKNOWN_FILES_FOR_MANAGED_COMPONENTS=1'
        )
        warn(warning)


def is_solve_required(project_requirements, solution):
    # type: (ProjectRequirements, SolvedManifest) -> bool

    if not solution.manifest_hash:
        print_info('Dependencies lock doesn\'t exist, solving dependencies.')
        return True

    if project_requirements.manifest_hash != solution.manifest_hash:
        print_info('Manifest files have changed, solving dependencies.')
        return True

    if solution.target and project_requirements.target != solution.target:
        print_info(
            'Target changed from {} to {}, solving dependencies.'.format(
                solution.target, project_requirements.target
            )
        )
        return True

    for component in solution.dependencies:
        try:
            # For downloadable volatile dependencies, like ones from git,
            # if manifest didn't change, no need to solve
            if component.source.downloadable and component.source.volatile:
                continue

            # For local components without version specified, nothing to do
            if not component.version.is_semver and component.source.volatile:
                continue

            # get the same version one
            try:
                component_versions = component.source.versions(
                    component.name, spec='=={}'.format(component.version.semver)
                )
            except FetchingError:
                print_warn(
                    'Version {} of dependency {} not found, probably it was deleted, solving dependencies.'.format(
                        component.version, component.name
                    )
                )
                return True
            except NetworkConnectionError:
                hint(
                    'Cannot establish a connection to the component registry. Skipping checks of dependency changes.'
                )
                return False

            component_version = component_versions.versions[0]

            # Handle meta components, like ESP-IDF, and volatile components, like local
            if component.source.meta or component.source.volatile:
                if component_version != component.version:
                    print_info(
                        'Dependency "{}" version has changed from {} to {}, '
                        'solving dependencies.'.format(
                            component, component.version, component_version
                        )
                    )
                    return True

            # Should check for all types of source, but after version checking
            if component_version.component_hash != component.component_hash:
                if component.source.volatile:
                    print_info(
                        'Dependency "{}" has changed, solving dependencies.'.format(component)
                    )
                    return True
                else:
                    raise InvalidComponentHashError(
                        'The hash sum of the component "{}" does not match '
                        'the one recorded in your dependencies.lock file. '
                        'This could be due to a potential spoofing of the download server, '
                        'or your lock file may have become corrupted. '
                        'Please review the lock file and verify the download server\'s '
                        'authenticity to ensure the component\'s security and integrity.'.format(
                            component
                        )
                    )

        except IndexError:
            print_info('Dependency "{}" version changed, solving dependencies.'.format(component))
            return True

    return False


def print_dot():
    print_info('.', nl=False)


@total_ordering
class DownloadedComponent:
    def __init__(self, downloaded_path, targets, version):  # type: (str, list[str], str) -> None
        self.downloaded_path = downloaded_path
        self.targets = targets
        self.version = version

    def __hash__(self):
        return hash(self.abs_path)

    def __eq__(self, other):
        if not isinstance(other, DownloadedComponent):
            return NotImplemented

        return self.abs_path == other.abs_path

    def __lt__(self, other):
        if not isinstance(other, DownloadedComponent):
            return NotImplemented

        return self.abs_path < other.abs_path

    @property
    def name(self):  # type: () -> str
        return os.path.basename(self.abs_path)

    @property
    def abs_path(self):
        return os.path.abspath(self.downloaded_path)

    @property
    def abs_posix_path(self):  # type: () -> str
        return Path(self.abs_path).as_posix()


def check_for_new_component_versions(project_requirements, old_solution):
    if getenv_bool('IDF_COMPONENT_CHECK_NEW_VERSION', False):
        # Check for newer versions of components
        solver = VersionSolver(project_requirements, old_solution)
        try:
            new_solution = solver.solve()
            new_deps_names = [dep.name for dep in new_solution.dependencies]
            updateable_components_messages = []

            for old_dep in old_solution.dependencies:
                # Check if the old dependency is present in the new solution
                if old_dep.name not in new_deps_names:
                    continue

                # Find index of old dependency in new_solution dependencies
                new_dep = new_solution.dependencies[new_deps_names.index(old_dep.name)]
                # Check if the version of the old dependency is different from the new one
                if old_dep.version != new_dep.version:
                    updateable_components_messages.append(
                        'Dependency "{}": "{}" -> "{}"'.format(
                            old_dep.name, old_dep.version, new_dep.version
                        )
                    )

            if updateable_components_messages:
                hint(
                    '\nFollowing dependencies have new versions available:\n{}'
                    '\nConsider running "idf.py update-dependencies" to update your lock file.\n'.format(
                        '\n'.join(updateable_components_messages)
                    )
                )

        except (SolverFailure, NetworkConnectionError):
            pass


def download_project_dependencies(
    project_requirements, lock_path, managed_components_path, is_idf_root_dependencies=False
):
    # type: (ProjectRequirements, str, str, bool) -> set[DownloadedComponent]
    """Solves dependencies and download components"""
    lock_manager = LockManager(lock_path)
    solution = lock_manager.load()
    check_manifests_targets(project_requirements)

    if is_solve_required(project_requirements, solution):
        solver = VersionSolver(project_requirements, solution, component_solved_callback=print_dot)

        try:
            solution = solver.solve()
        except SolverFailure as e:
            conflict_constraints = parse_root_dep_conflict_constraints(e)
            components_introduce_conflict = []
            for conflict_constraint in conflict_constraints:
                for manifest in project_requirements.manifests:
                    for dep in manifest.dependencies:
                        for source in dep.sources:
                            if Package(
                                dep.name, source
                            ) == conflict_constraint.package and dep.version_spec == str(
                                conflict_constraint.constraint
                            ):
                                components_introduce_conflict.append(manifest.name)
                                break

            if components_introduce_conflict:
                hint(
                    'Please check manifest file of the following component(s): {}'.format(
                        ', '.join(components_introduce_conflict)
                    )
                )
            raise SolverError(str(e))
        print_info('Updating lock file at %s' % lock_path)
        lock_manager.dump(solution)

    else:
        check_for_new_component_versions(
            project_requirements=project_requirements, old_solution=solution
        )
    # Download components
    downloaded_components = set()

    requirement_dependencies = []
    project_requirements_dependencies = [
        manifest.name for manifest in project_requirements.manifests
    ]

    for component in solution.dependencies:
        component_name_with_namespace = build_name(component.name)
        component_name = component_name_with_namespace.split('__')[-1]
        if (
            component_name_with_namespace not in project_requirements_dependencies
            and component_name not in project_requirements_dependencies
        ):
            requirement_dependencies.append(component)

    if os.path.exists(managed_components_path) and is_idf_root_dependencies is False:
        detect_unused_components(requirement_dependencies, managed_components_path)

    if requirement_dependencies:
        number_of_components = len(requirement_dependencies)
        changed_components = []
        print_info('Processing {} dependencies:'.format(number_of_components))

        for index, component in enumerate(requirement_dependencies):
            print_info(
                '[{index}/{num_components}] {component}'.format(
                    index=index + 1, num_components=number_of_components, component=str(component)
                )
            )
            fetcher = ComponentFetcher(component, managed_components_path)
            try:
                download_path = fetcher.download()
                if download_path:
                    fetcher.create_hash(download_path, component.component_hash)
                    downloaded_components.add(
                        DownloadedComponent(
                            download_path, component.targets, str(component.version)
                        )
                    )
            except ComponentModifiedError:
                changed_components.append(component.name)

        if changed_components:
            raise_component_modified_error(managed_components_path, changed_components)

    return downloaded_components
