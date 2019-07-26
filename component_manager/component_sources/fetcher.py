"""Small class that manages getting components to right path"""

import os

from component_manager.component_sources import BaseSource
from component_manager.version_solver.solver_result import SolvedComponent

from .errors import FetchingError


class ComponentFetcher(object):
    def __init__(
            self,
            solved_component,
            download_path,
            source=None,
    ):  # type: (SolvedComponent, str, BaseSource) -> None
        self.source = source if source else solved_component.source
        self.component = solved_component
        self.download_path = download_path

    def local_dir(self):
        return self.source.local_path()

    def up_to_date(self):  # type: () -> bool
        # TODO: verify that it's necessary to download component
        if self.source.component_hash_required:
            return False
        else:
            if not os.path.isdir(
                    self.source.local_path(
                        self.component.name,
                        self.component.version,
                        self.download_path,
                    )):
                raise FetchingError("Cannot install components")
            return True

    def fetch(self):  # type: () -> str
        """If necessary, it download and unpack component, returns local path to component directory"""
        if self.up_to_date():
            return self.local_dir()
        else:
            return self.source.fetch(
                self.component.name,
                self.component.version,
                self.download_path,
            )
