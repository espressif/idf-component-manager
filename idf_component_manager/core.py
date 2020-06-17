"""Core module of component manager"""
from __future__ import print_function

import os
from shutil import copyfile
from typing import Union

from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import Manifest, ManifestManager, SolvedManifest
from idf_component_tools.sources.fetcher import ComponentFetcher

from .version_solver.version_solver import VersionSolver


class ComponentManager(object):
    def __init__(self, path, lock_path=None, manifest_path=None):
        # type: (str, Union[None, str], Union[None, str]) -> None

        # Working directory
        self.path = path if os.path.isdir(path) else os.path.dirname(path)

        # Set path of manifest file for the project
        self.manifest_path = manifest_path or (os.path.join(path, 'idf_project.yml') if os.path.isdir(path) else path)

        # Lock path
        self.lock_path = lock_path or (os.path.join(path, 'dependencies.lock') if os.path.isdir(path) else path)

        # Components directory
        self.components_path = os.path.join(self.path, 'managed_components')

    def init_project(self):
        """Create manifest file if it doesn't exist in workdi"""
        if os.path.exists(self.manifest_path):
            print('`idf_project.yml` already exists in projects folder, skipping...')
        else:
            example_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'templates', 'idf_project_template.yml')
            print('Creating `idf_project.yml` in projects folder')
            copyfile(example_path, self.manifest_path)

    def install(self, components=None):
        manager = ManifestManager(self.manifest_path)
        manifest = Manifest.from_dict(manager.load())
        lock_manager = LockManager(self.lock_path)
        lock = lock_manager.load()
        solution = SolvedManifest.from_dict(manifest, lock)

        if manifest.manifest_hash != lock['manifest_hash']:
            solver = VersionSolver(manifest, lock)
            solution = solver.solve()

            # Create lock only if manifest exists
            if manager.exists():
                print('Updating lock file at %s' % self.lock_path)
                lock_manager.dump(solution)

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
