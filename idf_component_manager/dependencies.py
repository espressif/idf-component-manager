from idf_component_tools.errors import FetchingError
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

    if solution.dependencies:
        number_of_components = len(solution.dependencies)
        print('Processing {} dependencies:'.format(number_of_components))
        for index, component in enumerate(solution.dependencies):
            print('[{}/{}] {} ({})'.format(index + 1, number_of_components, component.name, component.version))
            download_paths = ComponentFetcher(component, managed_components_path).download()
            downloaded_component_paths.update(download_paths)

    return downloaded_component_paths
