"""Core module of component manager"""
from __future__ import print_function

import os
from typing import TYPE_CHECKING, List, Union

from component_management_tools.builders import ManifestBuilder
from component_management_tools.manifest import ManifestParser
from component_management_tools.sources.fetcher import ComponentFetcher

from .lock.manager import LockManager
from .version_solver.solver_result import SolverResult
from .version_solver.version_solver import VersionSolver

if TYPE_CHECKING:
    from component_management_tools.sources.base import BaseSource


class ComponentManager(object):
    def __init__(self, path, lock_path=None, manifest_path=None, sources=None):
        # type: (str, Union[None, str], Union[None, str], List[BaseSource]) -> None

        # Working directory
        self.path = path if os.path.isdir(path) else os.path.dirname(path)

        # Set path of manifest file for the project
        self.manifest_path = manifest_path or (os.path.join(path, 'idf_project.yml') if os.path.isdir(path) else path)

        # Lock path
        self.lock_path = lock_path or (os.path.join(path, 'dependencies.lock') if os.path.isdir(path) else path)

        # Components directory
        self.components_path = os.path.join(self.path, 'managed_components')

    def install(self, components=None):
        parser = ManifestParser(self.manifest_path).prepare()

        # TODO
        # def init_manifest(self):
        #     """Lazily create manifest file if it doesn't exist"""
        #     if not os.path.exists(self._path):
        #         example_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'manifest_example.yml')
        #         print("Info: manifest file wasn't found. Creating project's manifest")
        #         copyfile(example_path, self._path)

        #     def test_init_manifest(self):
        # tempdir = tempfile.mkdtemp()
        # try:
        #     manifest_path = os.path.join(tempdir, 'idf_project.yml')
        #     parser = ManifestParser(manifest_path)

        #     parser.init_manifest()

        #     with open(manifest_path, 'r') as f:
        #         assert f.readline().startswith('## Espressif')

        # finally:
        #     shutil.rmtree(tempdir)

        # TODO: Handle ManifestError

        return self
        manifest = ManifestBuilder(parser.manifest_tree).build()
        lock_manager = LockManager(self.lock_path)
        lock = lock_manager.load()
        solution = SolverResult.from_yaml(manifest, lock)

        if manifest.manifest_hash != lock['manifest_hash']:
            solver = VersionSolver(manifest, lock)
            solution = solver.solve()

            # Create lock only if manifest exists
            if parser.manifest_exists:
                print('Updating lock file at %s' % self.lock_path)
                lock_manager.dump(solution.as_ordered_dict())

        # Download components
        if not solution.solved_components:
            return solution

        components_count = len(solution.solved_components)
        count_string = 'dependencies' if components_count != 1 else 'dependency'
        print('Processing %s %s' % (components_count, count_string))
        for i, component in enumerate(solution.solved_components):
            line = ('[%d/%d] Processing component %s' % (i + 1, components_count, component.name))
            print(line)
            ComponentFetcher(component, self.components_path).download()

        print('Successfully processed %s %s ' % (components_count, count_string))
        return solution

    def prepare_dep_dirs(self, managed_components_list_file):
        # Install dependencies first
        # TODO: deal with IDF as component-bundle
        solution = self.install()

        # Include managed components in project directory
        with open(managed_components_list_file, 'w') as f:
            # TODO: write all components individually
            if solution.solved_components:
                f.write('__project_component_dir("%s")' % self.components_path)

    def inject_requrements(self, component_requires_file):
        pass
        # TODO: update requirements for known components
        # solution = self.install()
        # And update temporary requirements file
        # if solution.solved_components:
        #     with open(args.component_requires_file, 'r') as f:
        #         data = f.read()

        #     with open(args.component_requires_file, 'w') as f:
        #         for component in solution.solved_components:
        #             # TODO: deal with IDF as component-bundle
        #             if component.name == 'idf':
        #                 continue

        #             name_parts = component.name.split('/')
        #             f.write(
        #                 '\nidf_build_component("%s")' % os.path.join(args.project_dir,
        # "managed_components", *name_parts))

        #         f.write(data)

    def eject(self, components=None):
        print('Ejecting %s' % ', '.join(components))
        print('Not implemented yet')
