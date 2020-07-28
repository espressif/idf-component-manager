"""Small class that manages getting components to right path using system-wide cache"""

import os
from typing import TYPE_CHECKING

from ..errors import FetchingError
from ..hash_tools import validate_dir
from ..manifest import SolvedComponent

if TYPE_CHECKING:
    from . import BaseSource


class ComponentFetcher(object):
    def __init__(
        self,
        solved_component,
        components_path,
        source=None,
    ):  # type: (SolvedComponent, str, BaseSource) -> None
        self.source = source if source else solved_component.source
        self.component = solved_component
        self.components_path = components_path

    def up_to_date(self, path):  # type: (str) -> bool
        if self.source.component_hash_required and not self.component.component_hash:
            raise FetchingError('Cannot install component with unknown hash')

        if self.source.downloadable:
            if not os.path.isdir(path):
                return False

            if self.component.component_hash:
                return validate_dir(path, self.component.component_hash)

        return True

    def download(self):  # type: () -> str
        """If necessary, it downloads component and returns local path to component directory"""
        name_parts = self.component.name.split('/')
        managed_path = os.path.join(self.components_path, '__'.join(name_parts))

        # Check if component is up to date in managed components path
        # TODO: fix up_to_date function
        # if self.source.downloadable and self.up_to_date(managed_path):
        #     return managed_path

        return self.source.download(self.component, managed_path)
