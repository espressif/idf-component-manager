# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Classes to work with Espressif Component Web Service"""

from .api_client_errors import ComponentNotFound, VersionNotFound
from .component_details import ComponentDetailsWithStorageURL
from .storage_client import StorageClient


class MultiStorageClient:
    def __init__(self, storage_urls=None, sources=None):
        self._storage_urls = storage_urls
        if not sources:
            sources = []
        self.sources = sources

    @property
    def storage_urls(self):
        if not self._storage_urls:
            self._storage_urls = []
        return self._storage_urls

    def versions(self, component_name, spec='*'):
        latest_cmp_with_version = None
        for storage_url in self.storage_urls:
            api_client = StorageClient(storage_url, sources=self.sources)
            try:
                cmp_with_versions = api_client.versions(component_name=component_name, spec=spec)
                if cmp_with_versions.versions:
                    return cmp_with_versions
                latest_cmp_with_version = cmp_with_versions
            except ComponentNotFound:
                pass

        if latest_cmp_with_version:
            return latest_cmp_with_version

        raise ComponentNotFound('Component "{}" not found'.format(component_name))

    def component(
        self, component_name, version=None
    ):  # type: (str, str | None) -> ComponentDetailsWithStorageURL
        error_message = ''
        for storage_url in self.storage_urls:
            api_client = StorageClient(storage_url, sources=self.sources)
            try:
                return api_client.component(component_name=component_name, version=version)
            except (VersionNotFound, ComponentNotFound) as err:
                error_message = str(err)

        raise VersionNotFound(error_message)
