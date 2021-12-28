"""Small class that manages getting components to right path using system-wide cache"""

import os
import re
from io import open

from ..build_system_tools import build_name
from ..errors import ComponentModifiedError, InvalidComponentHashError
from ..hash_tools import hash_dir
from ..manifest import SolvedComponent
from ..manifest.constants import SHA256_RE

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
        self.managed_path = os.path.join(self.components_path, build_name(self.component.name))

    def download(self):  # type: () -> List[str]
        """If necessary, it downloads component and returns local path to component directory"""
        hash_file = os.path.join(self.managed_path, '.component_hash')

        if os.path.isdir(self.managed_path) and os.path.exists(hash_file):
            with open(hash_file, mode='r', encoding='utf-8') as f:
                hash_from_file = f.read().strip()
            hash_directory = hash_dir(self.managed_path)

            if hash_directory != hash_from_file:
                if re.match(SHA256_RE, hash_from_file):
                    raise ComponentModifiedError(
                        'Component directory was modified on the disk since the last run of '
                        'the CMake')
                else:
                    raise InvalidComponentHashError(
                        'File .component_hash for component "{}" in the managed '
                        'components directory cannot be parsed. This file is used by the '
                        'component manager for component integrity checks. If this file '
                        'exists in the component source, please ask the component '
                        'maintainer to remove it.'.format(self.component.name))

        return self.source.download(self.component, self.managed_path)

    def create_hash(self, paths, component_hash):
        if self.component.source.downloadable:
            hash_file = os.path.join(paths[0], '.component_hash')

            if not os.path.isfile(hash_file):
                with open(hash_file, mode='w+', encoding='utf-8') as f:
                    f.write(u'{}'.format(component_hash))
