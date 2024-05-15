# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_tools.build_system_tools import get_idf_path, get_idf_version
from idf_component_tools.semver import match
from idf_component_tools.utils import ComponentWithVersions, HashedComponentVersion, Literal

from .base import BaseSource


class IDFSource(BaseSource):
    type: Literal['idf'] = 'idf'  # type: ignore

    @property
    def meta(self):
        return True

    def normalized_name(self, name: str) -> str:
        return self.type

    def versions(self, name, spec='*', target=None):
        local_idf_version = get_idf_version()

        if match(spec, local_idf_version):
            versions = [HashedComponentVersion(local_idf_version)]
        else:
            versions = []

        return ComponentWithVersions(name=name, versions=versions)

    def download(self, component, download_path):
        get_idf_path()
        return None
