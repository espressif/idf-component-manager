from idf_component_tools.build_system_tools import get_env_idf_target
from idf_component_tools.errors import FetchingError
from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import Manifest, ProjectRequirements
from idf_component_tools.sources.fetcher import ComponentFetcher

from .version_solver.version_solver import VersionSolver

try:
    from typing import List, Set
except ImportError:
    pass


def check_manifests_targets(manifests):  # type: (List[Manifest]) -> None
    target = get_env_idf_target()

    for manifest in manifests:
        if not manifest.targets:
            continue

        if target not in manifest.targets:
            raise FetchingError('Component "{}" does not support target {}'.format(manifest.name, target))


def download_project_dependencies(manifests, lock_path, managed_components_path):
    # type: (List[Manifest], str, str) -> Set[str]
    '''Solves dependencies and download components'''
    project_requirements = ProjectRequirements(manifests)
    lock_manager = LockManager(lock_path)
    solution = lock_manager.load()
    if project_requirements.manifest_hash != solution.manifest_hash:
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
            print('[{}/{}] {}'.format(index + 1, number_of_components, component.name))
            download_paths = ComponentFetcher(component, managed_components_path).download()
            downloaded_component_paths.update(download_paths)

    return downloaded_component_paths
