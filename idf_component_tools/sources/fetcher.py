# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Small class that manages getting components to right path using system-wide cache"""

import typing as t
from pathlib import Path

from idf_component_tools.build_system_tools import build_name
from idf_component_tools.hash_tools.constants import HASH_FILENAME
from idf_component_tools.manifest import SolvedComponent

if t.TYPE_CHECKING:
    pass


class ComponentFetcher:
    def __init__(
        self,
        solved_component: SolvedComponent,
        managed_components_path: t.Union[str, Path],
    ) -> None:
        self.source = solved_component.source
        self.component = solved_component
        self.component_path = Path(managed_components_path) / build_name(self.component.name)

    def download(self) -> t.Optional[str]:
        """Download component to the managed components directory"""

        download_path = self.source.download(self.component, self.component_path.as_posix())

        if download_path:
            self.create_hash()

        return download_path

    def create_hash(self) -> None:
        """Create file with hash of the component"""

        if not self.source.downloadable:
            return

        hash_file = self.component_path / HASH_FILENAME

        with open(hash_file, mode='w', encoding='utf-8') as f:
            f.write(f'{self.component.component_hash}')
