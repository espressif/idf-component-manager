from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import ManifestManager, ProjectRequirements
from idf_component_tools.sources.fetcher import ComponentFetcher

from .version_solver.version_solver import VersionSolver

try:
    from typing import List, Set
except ImportError:
    pass


def download_project_dependencies(manifest_paths, lock_path, managed_components_path):
    # type: (List[dict], str, str) -> Set[str]
    '''Solves dependencies and download components'''
    manifests = [ManifestManager(component['path'], component['name']).load() for component in manifest_paths]
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
