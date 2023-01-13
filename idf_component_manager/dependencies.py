# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import shutil

from idf_component_manager.utils import print_info
from idf_component_tools.build_system_tools import build_name
from idf_component_tools.errors import ComponentModifiedError, FetchingError, SolverError, hint, warn
from idf_component_tools.hash_tools import ValidatingHashError, validate_dir_with_hash_file
from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import ProjectRequirements, SolvedComponent, SolvedManifest
from idf_component_tools.sources.fetcher import ComponentFetcher

from .core_utils import raise_component_modified_error
from .version_solver.helper import parse_root_dep_conflict_constraints
from .version_solver.mixology.failure import SolverFailure
from .version_solver.mixology.package import Package
from .version_solver.version_solver import VersionSolver


def check_manifests_targets(project_requirements):  # type: (ProjectRequirements) -> None
    for manifest in project_requirements.manifests:
        if not manifest.targets:
            continue

        if project_requirements.target not in manifest.targets:
            raise FetchingError(
                'Component "{}" does not support target {}'.format(manifest.name, project_requirements.target))


def get_unused_components(unused_files_with_components, managed_components_path):  # type: (set[str], str) -> set[str]
    unused_components = set()

    for component in unused_files_with_components:
        try:
            validate_dir_with_hash_file(os.path.join(managed_components_path, component))
            unused_components.add(component)
        except ValidatingHashError:
            pass

    return unused_components


def detect_unused_components(
        requirement_dependencies, managed_components_path):  # type: (list[SolvedComponent], str) -> None
    downloaded_components = os.listdir(managed_components_path)
    unused_files_with_components = set(downloaded_components) - {
        build_name(component.name)
        for component in requirement_dependencies
    }
    unused_components = get_unused_components(unused_files_with_components, managed_components_path)
    unused_files = unused_files_with_components - unused_components
    if unused_components:
        print_info('Deleting {} unused components'.format(len(unused_components)))
        for unused_component_name in unused_components:
            print_info(' {}'.format(unused_component_name))
            shutil.rmtree(os.path.join(managed_components_path, unused_component_name))
    if unused_files and os.getenv('IGNORE_UNKNOWN_FILES_FOR_MANAGED_COMPONENTS') != '1':
        warning = '{} unexpected files and directories were found in the "managed_components" directory:'.format(
            len(unused_files))

        for unexpected_name in unused_files:
            warning += ' {}'.format(unexpected_name)

        warning += (
            '\nContent of the managed components directory is managed automatically and it\'s not recommended to '
            'place any files there manually. To suppress this warning set the environment variable: '
            'IGNORE_UNKNOWN_FILES_FOR_MANAGED_COMPONENTS=1')
        warn(warning)


def is_solve_required(project_requirements, solution):
    # type: (ProjectRequirements, SolvedManifest) -> bool

    if project_requirements.manifest_hash != solution.manifest_hash\
            or (solution.target and project_requirements.target != solution.target):
        return True

    for component in solution.dependencies:
        if not component.source.meta:
            continue

        try:
            component_version = component.source.versions(component.name).versions[0]

            if component_version != component.version:
                return True
        except IndexError:
            return True

    return False


def print_dot():
    print_info('.', nl=False)


def download_project_dependencies(project_requirements, lock_path, managed_components_path):
    # type: (ProjectRequirements, str, str) -> tuple[set[str], dict[str, str]]
    '''Solves dependencies and download components'''
    lock_manager = LockManager(lock_path)
    solution = lock_manager.load()
    check_manifests_targets(project_requirements)

    if is_solve_required(project_requirements, solution):
        print_info('Solving dependencies requirements')
        solver = VersionSolver(project_requirements, solution, component_solved_callback=print_dot)

        try:
            solution = solver.solve()
        except SolverFailure as e:
            conflict_constraints = parse_root_dep_conflict_constraints(e)
            components_introduce_conflict = []
            for conflict_constraint in conflict_constraints:
                for manifest in project_requirements.manifests:
                    for dep in manifest.dependencies:
                        if (Package(dep.name, dep.source) == conflict_constraint.package
                                and dep.version_spec == str(conflict_constraint.constraint)):
                            components_introduce_conflict.append(manifest.name)
                            break

            if components_introduce_conflict:
                hint(
                    'Please check manifest file of the following component(s): {}'.format(
                        ', '.join(components_introduce_conflict)))

            raise SolverError(str(e))

        print_info('Updating lock file at %s' % lock_path)
        lock_manager.dump(solution)

    # Download components
    downloaded_component_paths = set()
    downloaded_component_version_dict = dict()
    requirement_dependencies = []
    project_requirements_dependencies = [manifest.name for manifest in project_requirements.manifests]

    for component in solution.dependencies:
        component_name_with_namespace = build_name(component.name)
        component_name = component_name_with_namespace.split('__')[-1]
        if component_name_with_namespace not in project_requirements_dependencies \
                and component_name not in project_requirements_dependencies:
            requirement_dependencies.append(component)

    if os.path.exists(managed_components_path):
        detect_unused_components(requirement_dependencies, managed_components_path)

    if requirement_dependencies:
        number_of_components = len(requirement_dependencies)
        changed_components = []
        print_info('Processing {} dependencies:'.format(number_of_components))

        for index, component in enumerate(requirement_dependencies):
            print_info('[{}/{}] {} ({})'.format(index + 1, number_of_components, component.name, component.version))
            fetcher = ComponentFetcher(component, managed_components_path)
            try:
                download_path = fetcher.download()
                if download_path:
                    fetcher.create_hash(download_path, component.component_hash)
                    downloaded_component_paths.add(download_path)
                    # Save versions of downloadable components
                    downloaded_component_version_dict[download_path] = str(component.version)
            except ComponentModifiedError:
                changed_components.append(component.name)

        if changed_components:
            raise_component_modified_error(managed_components_path, changed_components)

    return downloaded_component_paths, downloaded_component_version_dict
