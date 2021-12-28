import os
from textwrap import dedent

from idf_component_tools.build_system_tools import build_name
from idf_component_tools.errors import ComponentModifiedError, FetchingError
from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import ProjectRequirements
from idf_component_tools.sources.fetcher import ComponentFetcher

from .version_solver.version_solver import VersionSolver

try:
    from typing import Set
except ImportError:
    pass


def check_manifests_targets(project_requirements):  # type: (ProjectRequirements) -> None
    for manifest in project_requirements.manifests:
        if not manifest.targets:
            continue

        if project_requirements.target not in manifest.targets:
            raise FetchingError(
                'Component "{}" does not support target {}'.format(manifest.name, project_requirements.target))


def download_project_dependencies(project_requirements, lock_path, managed_components_path):
    # type: (ProjectRequirements, str, str) -> Set[str]
    '''Solves dependencies and download components'''
    lock_manager = LockManager(lock_path)
    solution = lock_manager.load()
    check_manifests_targets(project_requirements)

    if (project_requirements.has_dependencies
            and (project_requirements.manifest_hash != solution.manifest_hash or
                 (solution.target and project_requirements.target != solution.target))):
        print('Solving dependencies requirements')
        solver = VersionSolver(project_requirements, solution)
        solution = solver.solve()

        print('Updating lock file at %s' % lock_path)
        lock_manager.dump(solution)

    # Download components
    downloaded_component_paths = set()
    requirement_dependencies = []
    project_requirements_dependencies = [manifest.name for manifest in project_requirements.manifests]

    for component in solution.dependencies:
        component_name_with_namespace = build_name(component.name)
        component_name = component_name_with_namespace.split('__')[-1]
        if component_name_with_namespace not in project_requirements_dependencies \
                and component_name not in project_requirements_dependencies:
            requirement_dependencies.append(component)

    if requirement_dependencies:
        number_of_components = len(requirement_dependencies)
        changed_components = []
        print('Processing {} dependencies:'.format(number_of_components))

        for index, component in enumerate(requirement_dependencies):
            print('[{}/{}] {} ({})'.format(index + 1, number_of_components, component.name, component.version))
            fetcher = ComponentFetcher(component, managed_components_path)
            try:
                download_paths = fetcher.download()
                fetcher.create_hash(download_paths, component.component_hash)
                downloaded_component_paths.update(download_paths)
            except ComponentModifiedError:
                changed_components.append(component.name)

        if changed_components:
            project_path = os.path.split(managed_components_path)[0]
            component_example_name = changed_components[0].replace('/', '__')
            managed_component_folder = os.path.join(managed_components_path, component_example_name)
            component_folder = os.path.join(project_path, 'components', component_example_name)
            hash_path = os.path.join(managed_component_folder, '.component_hash')
            error = """
                Some components ({0}) in the
                "managed_components" directory were modified on the disk since the last run of the CMake. Content of
                this directory is managed automatically.

                If you want to keep the changes, you can move the directory with the component to the "components"
                directory of your project.

                I.E. for "{1}" run:

                mv {2} {3}

                Or, if you want to discard the changes remove the ".component_hash" file from the component's directory.

                I.E. for "{1}" run:

                rm {4}
            """.format(
                ', '.join(changed_components), component_example_name, managed_component_folder, component_folder,
                hash_path)
            raise ComponentModifiedError(dedent(error))

    return downloaded_component_paths
