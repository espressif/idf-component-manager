"""Small class that manages getting components to right path using system-wide cache"""

import os

from ..build_system_tools import build_name
from ..errors import FetchingError
from ..hash_tools import validate_dir
from ..manifest import SolvedComponent

try:
    from typing import TYPE_CHECKING, List

    if TYPE_CHECKING:
        from . import BaseSource
except ImportError:
    pass


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

    def download(self):  # type: () -> List[str]
        """If necessary, it downloads component and returns local path to component directory"""
        managed_path = os.path.join(self.components_path, build_name(self.component.name))

        return self.source.download(self.component, managed_path)
