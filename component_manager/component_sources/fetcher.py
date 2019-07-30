"""Small class that manages getting components to right path using system-wide cache"""

import os
import shutil

from component_manager.component_sources import BaseSource
from component_manager.lock.hash_tools import HashTools
from component_manager.utils.file_cache import FileCache
from component_manager.version_solver.solver_result import SolvedComponent

from .errors import FetchingError


class ComponentFetcher(object):
    def __init__(
            self,
            solved_component,
            components_path,
            cache_path=None,
            source=None,
    ):  # type: (SolvedComponent, str, str, BaseSource) -> None
        self.source = source if source else solved_component.source
        self.component = solved_component
        self.components_path = components_path
        self.managed_path = os.path.join(self.components_path, self.component.name)
        self.cache_path = cache_path or FileCache.path()

    def up_to_date(self, path):  # type: (str) -> bool
        if self.source.component_hash_required and not self.component.component_hash:
            raise FetchingError("Cannot install component with unknown hash")

        if self.source.downloadable:
            if not os.path.isdir(path):
                return False

            if self.component.component_hash:
                return HashTools.validate_dir(path, self.component.component_hash)

        return True

    def download(self):  # type: () -> str
        """If necessary, it downloads component and returns local path to component directory"""
        if self.source.downloadable:
            # Check if component is up to date in managed components path
            if not self.up_to_date(self.managed_path):
                print("Component %s wan't found in %s" % (self.component.name, self.managed_path))
                # Check if it's up to date in the cache:
                component_cache_path = os.path.join(
                    self.cache_path,
                    self.source.unique_path(self.component.name, self.component.version),
                )

                if not self.up_to_date(component_cache_path):
                    print("Cached component %s wan't found in %s" % (self.component.name, component_cache_path))
                    self.source.download(self.component.name, self.component.version, component_cache_path)

                    if os.path.isdir(self.managed_path):
                        shutil.rmtree(self.managed_path)

                    shutil.copytree(component_cache_path, self.managed_path)

            return self.managed_path

        return self.source.download(self.component.name, self.component.version, self.managed_path)
