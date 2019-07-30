"""Core module of component manager"""
from __future__ import print_function

import os
from typing import List, Union

from .cmake_builder import CMakeBuilder
from .component_sources import BaseSource, ComponentFetcher, SourceStorage
from .lock.manager import LockManager
from .manifest_builder import ManifestBuilder
from .manifest_pipeline import ManifestParser
from .version_solver import VersionSolver
from .version_solver.solver_result import SolverResult


class ComponentManager(object):
    def __init__(self, path, lock_path=None, manifest_path=None,
                 sources=None):  # type: (str, Union[None, str], Union[None, str], List[BaseSource]) -> None

        # That may take a while to init sources (in case of git), so all of them are stored between launches
        self.sources = SourceStorage()

        # Set path of manifest file for the project
        self.manifest_path = manifest_path or (os.path.join(path, "idf_project.yml") if os.path.isdir(path) else path)
        print("\033[1;35;40m Manifest path", self.manifest_path, "\033[0m")

        # Lock path
        self.lock_path = lock_path or (os.path.join(path, "dependencies.lock") if os.path.isdir(path) else path)
        print("\033[1;35;40m Lock path", self.lock_path, "\033[0m")

        # Working directory
        self.path = path if os.path.isdir(path) else os.path.dirname(path)

        # Components directory
        self.components_path = os.path.join(self.path, "managed_components")

    def add(self, components):
        print("Adding %s to manifest" % ", ".join(components))
        print("Not implemented yet")

    def install(self):
        parser = ManifestParser(self.manifest_path).prepare()
        manifest = ManifestBuilder(parser.manifest_tree, self.sources).build()
        lock_manager = LockManager(self.lock_path)
        lock = lock_manager.load()
        solution = SolverResult.from_yaml(manifest, lock)

        if manifest.manifest_hash != lock["manifest_hash"]:
            print("Updating lock file")
            solver = VersionSolver(manifest, lock)
            solution = solver.solve()
            lock_manager.dump(solution.as_ordered_dict())

        # Download components
        print("Installing components from manifest")
        for component in solution.solved_components:
            # Check hash if hash present and download component if necessary
            path = ComponentFetcher(component, self.components_path).download()
            print("Installed component %s to %s" % (component.name, path))

    def update(self, components=None):
        if components is None:
            components = []
        print("Updating %s" % ", ".join(components))
        print("Not implemented yet")

    def eject(self, components):
        print("Ejecting %s" % ", ".join(components))
        print("Not implemented yet")

    def prebuild(self):
        # TODO: read build directory from IDF
        path = os.path.join(self.path, "build")

        # check lock file state
        self.install()

        # TODO: Check components in other sources

        # TODO: Download all required components

        # TODO: Load flattened dependecy tree

        CMakeBuilder(path).build()
        # Generate CMake file
