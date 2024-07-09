# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Small class that manages getting components to right path using system-wide cache"""

import os
import typing as t

from idf_component_tools import ComponentManagerSettings
from idf_component_tools.build_system_tools import build_name
from idf_component_tools.errors import (
    ComponentModifiedError,
    FetchingError,
    InvalidComponentHashError,
)
from idf_component_tools.hash_tools.constants import HASH_FILENAME
from idf_component_tools.hash_tools.errors import (
    HashDoesNotExistError,
    HashNotEqualError,
    HashNotSHA256Error,
)
from idf_component_tools.hash_tools.validate_managed_component import (
    validate_managed_component_by_hashfile,
    validate_managed_component_hash,
)
from idf_component_tools.manifest import SolvedComponent

if t.TYPE_CHECKING:
    from . import BaseSource


class ComponentFetcher:
    def __init__(
        self,
        solved_component: SolvedComponent,
        components_path: str,
        source: t.Optional['BaseSource'] = None,
    ) -> None:
        self.source = source if source else solved_component.source
        self.component = solved_component
        self.components_path = components_path
        self.managed_path = os.path.join(self.components_path, build_name(self.component.name))

    def download(self) -> t.Optional[str]:
        """If necessary, it downloads component and returns local path to component directory"""
        try:
            if self.source.downloadable and not ComponentManagerSettings().STRICT_CHECKSUM:
                if not self.component.component_hash:
                    raise FetchingError('Cannot install component with unknown hash')

                validate_managed_component_by_hashfile(
                    self.managed_path, self.component.component_hash
                )
            else:
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

    def create_hash(self, path: str, component_hash: t.Optional[str]) -> None:
        if self.component.source.downloadable:
            hash_file = os.path.join(path, HASH_FILENAME)

            if not os.path.isfile(hash_file):
                with open(hash_file, mode='w+', encoding='utf-8') as f:
                    f.write(f'{component_hash}')
