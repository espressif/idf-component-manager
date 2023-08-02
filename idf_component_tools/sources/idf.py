# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from .. import semver
from ..build_system_tools import get_idf_path, get_idf_version
from ..manifest import ComponentWithVersions, HashedComponentVersion
from .base import BaseSource

try:
    from typing import Dict
except ImportError:
    pass


class IDFSource(BaseSource):
    NAME = 'idf'

    @staticmethod
    def create_sources_if_valid(name, details, manifest_manager=None):
        if name == IDFSource.NAME:
            return [IDFSource(details, manifest_manager=manifest_manager)]
        return None

    @property
    def hash_key(self):
        return self.NAME

    @property
    def meta(self):
        return True

    def normalized_name(self, name):  # type: (str) -> str
        return self.NAME

    def versions(self, name, details=None, spec='*', target=None):
        local_idf_version = get_idf_version()

        if semver.match(spec, local_idf_version):
            versions = [HashedComponentVersion(local_idf_version)]
        else:
            versions = []

        return ComponentWithVersions(name=name, versions=versions)

    def download(self, component, download_path):
        get_idf_path()
        return None

    def serialize(self):  # type: () -> Dict
        return {'type': self.name}
