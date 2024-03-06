# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Small class that manages getting components to right path using system-wide cache"""

import os
from typing import TYPE_CHECKING

from idf_component_tools.hash_tools.constants import HASH_FILENAME
from idf_component_tools.hash_tools.errors import (
    HashDoesNotExistError,
    HashNotEqualError,
    HashNotSHA256Error,
)
from idf_component_tools.hash_tools.validate_managed_component import (
    validate_managed_component_hash,
)

from ..build_system_tools import build_name
from ..errors import ComponentModifiedError, InvalidComponentHashError
from ..manifest.solved_component import SolvedComponent

if TYPE_CHECKING:
    from . import BaseSource


class ComponentFetcher:
    def __init__(
        self,
        solved_component,
        components_path,
        source=None,
    ):  # type: (SolvedComponent, str, BaseSource | None) -> None
        self.source = source if source else solved_component.source
        self.component = solved_component
        self.components_path = components_path
        self.managed_path = os.path.join(self.components_path, build_name(self.component.name))

    def download(self):  # type: () -> str | None
        """If necessary, it downloads component and returns local path to component directory"""
        try:
            validate_managed_component_hash(self.managed_path)
        except HashNotEqualError:
            raise ComponentModifiedError(
                'Component directory was modified on the disk since the last run of ' 'the CMake'
            )
        except HashNotSHA256Error:
            raise InvalidComponentHashError(
                'File .component_hash for component "{}" in the managed '
                'components directory cannot be parsed. This file is used by the '
                'component manager for component integrity checks. If this file '
                'exists in the component source, please ask the component '
                'maintainer to remove it.'.format(self.component.name)
            )
        except HashDoesNotExistError:
            pass

        return self.source.download(self.component, self.managed_path)

    def create_hash(self, path, component_hash):  # type: (str, None | str) -> None
        if self.component.source.downloadable:
            hash_file = os.path.join(path, HASH_FILENAME)

            if not os.path.isfile(hash_file):
                with open(hash_file, mode='w+', encoding='utf-8') as f:
                    f.write(f'{component_hash}')
