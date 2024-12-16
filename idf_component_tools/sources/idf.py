# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import typing as t

from idf_component_tools.build_system_tools import get_idf_path, get_idf_version
from idf_component_tools.hash_tools.checksums import ChecksumsModel
from idf_component_tools.semver import match
from idf_component_tools.utils import ComponentWithVersions, HashedComponentVersion, Literal

from .base import BaseSource

if t.TYPE_CHECKING:
    from idf_component_tools.manifest import SolvedComponent


class IDFSource(BaseSource):
    type: Literal['idf'] = 'idf'  # type: ignore

    @property
    def meta(self):
        return True

    def normalized_name(self, name: str) -> str:  # noqa: ARG002
        return self.type

    def versions(self, name, spec='*', target=None):  # noqa: ARG002
        local_idf_version = get_idf_version()

        if match(spec, local_idf_version):
            versions = [HashedComponentVersion(local_idf_version)]
        else:
            versions = []

        return ComponentWithVersions(name=name, versions=versions)

    def download(self, component, download_path):  # noqa: ARG002
        get_idf_path()
        return None

    def version_checksums(self, component: 'SolvedComponent') -> t.Optional[ChecksumsModel]:  # noqa: ARG002
        return None
