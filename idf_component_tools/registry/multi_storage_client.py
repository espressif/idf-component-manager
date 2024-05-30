# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Classes to work with ESP Component Registry"""

import typing as t
from collections import namedtuple
from functools import lru_cache

from idf_component_tools.constants import (
    DEFAULT_NAMESPACE,
    IDF_COMPONENT_REGISTRY_URL,
    IDF_COMPONENT_STORAGE_URL,
)
from idf_component_tools.messages import warn
from idf_component_tools.utils import ComponentWithVersions

from .api_client import APIClient
from .client_errors import ComponentNotFound, VersionNotFound
from .storage_client import StorageClient

ComponentInfo = namedtuple('ComponentInfo', ['data', 'storage_url'])


class MultiStorageClient:
    """
    In each service profile, we have a bunch of urls:

    - registry_url: the URL of the component registry
    - storage_url: a list of URLs of the component storage
    - local_storage_url: a list of URLs of the local component storage

    Besides, each registry_url also have one online storage_url,
    used for downloading the components.
    """

    def __init__(
        self,
        registry_url: t.Optional[str] = None,
        storage_urls: t.Optional[t.List[str]] = None,
        local_storage_urls: t.Optional[t.List[str]] = None,
        api_token: t.Optional[str] = None,
        default_namespace: t.Optional[str] = None,
        local_first_mode: bool = True,
    ) -> None:
        self.registry_url = registry_url
        self.storage_urls = storage_urls or []
        self.local_storage_urls = local_storage_urls or []

        self.api_token = api_token
        self.default_namespace = default_namespace or DEFAULT_NAMESPACE

        self.local_first_mode = local_first_mode

    @property
    @lru_cache(1)
    def registry_storage_url(self) -> t.Optional[str]:
        if self.registry_url:
            if self.registry_url == IDF_COMPONENT_REGISTRY_URL:
                return IDF_COMPONENT_STORAGE_URL

            return APIClient(self.registry_url).api_information()['components_base_url']

        return None

    @property
    @lru_cache(1)
    def registry_storage_client(self) -> t.Optional[StorageClient]:
        if self.registry_storage_url:
            return StorageClient(self.registry_storage_url)

        return None

    @property
    @lru_cache(1)
    def storage_clients(self):
        clients = [StorageClient(url) for url in [*self.local_storage_urls, *self.storage_urls]]
        if self.registry_storage_client:
            clients.append(self.registry_storage_client)

        return clients

    def versions(self, component_name: str, spec: str = '*') -> ComponentWithVersions:
        cmp_with_versions = ComponentWithVersions(component_name, [])

        for storage_client in self.storage_clients:
            try:
                _cmp_with_versions = storage_client.versions(
                    component_name=component_name,
                    spec=spec,
                )
                cmp_with_versions.merge(_cmp_with_versions)
            except ComponentNotFound:
                pass

            if self.local_first_mode and cmp_with_versions.versions:
                return cmp_with_versions

        if not cmp_with_versions.versions:
            warn(f'Component "{component_name}" not found')

        return cmp_with_versions

    def component(self, component_name: str, version: t.Optional[str] = None) -> t.Dict[str, t.Any]:
        error_message = ''
        for storage_client in self.storage_clients:
            try:
                return storage_client.component(component_name=component_name, version=version)
            except (VersionNotFound, ComponentNotFound) as err:
                error_message = str(err)

        raise VersionNotFound(error_message)

    def get_component_info(self, component_name, spec):
        error_message = ''
        for storage_client in self.storage_clients:
            try:
                info = storage_client.get_component_info(component_name=component_name, spec=spec)
                return ComponentInfo(info, storage_client.storage_url)
            except (VersionNotFound, ComponentNotFound) as err:
                error_message = str(err)

        raise VersionNotFound(error_message)

    def version_dependencies(self, version):
        client = self.storage_clients[0]
        return client.version_dependencies(version)
