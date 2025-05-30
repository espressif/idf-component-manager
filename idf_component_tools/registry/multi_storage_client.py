# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Classes to work with ESP Component Registry"""

import typing as t
from functools import lru_cache

from idf_component_manager.utils import VersionSolverResolution
from idf_component_tools.constants import (
    DEFAULT_NAMESPACE,
    IDF_COMPONENT_REGISTRY_URL,
    IDF_COMPONENT_STORAGE_URL,
)
from idf_component_tools.messages import debug, warn
from idf_component_tools.utils import ComponentWithVersions

from ..manifest import ComponentRequirement
from ..semver import Version
from .api_client import APIClient
from .client_errors import ComponentNotFound, VersionNotFound
from .storage_client import StorageClient


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
        if self.registry_url and self.registry_url.rstrip('/') == IDF_COMPONENT_REGISTRY_URL.rstrip(
            '/'
        ):
            return IDF_COMPONENT_STORAGE_URL
        elif self.registry_url:
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
    def local_storage_clients(self):
        return [StorageClient(url) for url in self.local_storage_urls]

    @property
    @lru_cache(1)
    def profile_storage_clients(self):
        return [StorageClient(url) for url in self.storage_urls]

    @property
    @lru_cache(1)
    def storage_clients(self):
        yield from self.local_storage_clients
        yield from self.profile_storage_clients
        if self.registry_storage_client:
            yield self.registry_storage_client

    def versions(self, component_name: str, spec: str = '*') -> ComponentWithVersions:
        component_name = component_name.lower()
        cmp_with_versions = ComponentWithVersions(component_name, [])

        for storage_client in self.storage_clients:
            try:
                debug(
                    'Fetching versions of component "%s" with spec "%s" from %s',
                    component_name,
                    spec,
                    storage_client.storage_url,
                )
                _cmp_with_versions = storage_client.versions(
                    component_name=component_name,
                    spec=spec,
                )
                debug(
                    'Fetched versions: %s',
                    ', '.join(str(version) for version in _cmp_with_versions.versions),
                )

                cmp_with_versions.merge(_cmp_with_versions)
            except ComponentNotFound:
                debug('Nothing found')
                pass

            if self.local_first_mode and cmp_with_versions.versions:
                debug('local_first_mode is enabled, skipping checking other storage clients')
                return cmp_with_versions

        if not cmp_with_versions.versions:
            warn(f'Component "{component_name}" not found')

        return cmp_with_versions

    def component(self, component_name: str, version: t.Optional[str] = None) -> t.Dict[str, t.Any]:
        """
        Get component manifest for given component name and spec. All urls are rewritten to storage urls.

        :param component_name: The name of the component
        :param version: The version spec of the component
        :return: The component manifest. shall use download_url to download the component
        """
        error_message = ''
        for storage_client in self.storage_clients:
            try:
                return storage_client.component(component_name=component_name, version=version)
            except (VersionNotFound, ComponentNotFound) as err:
                error_message = str(err)

        raise VersionNotFound(error_message)

    def get_component_versions(
        self,
        requirement: ComponentRequirement,
        *,
        resolution: VersionSolverResolution = VersionSolverResolution.ALL,
    ) -> t.Tuple[ComponentWithVersions, str]:
        """
        Get all versions of the component from all storage clients (local storages are ignored)

        Include all versions even the optional ones

        :param requirement: ComponentRequirement instance
        :param resolution: The resolution of the version solver
        :return: (ComponentWithVersions, storage_url)
        """
        # local_storage_urls shall not be used when create partial mirror
        _clients = self.profile_storage_clients.copy()
        if self.registry_storage_client:
            _clients.append(self.registry_storage_client)

        error_message = ''

        specs = [requirement.version]  # base one
        # optional ones
        for opt_dep in [*(requirement.matches or []), *(requirement.rules or [])]:
            if opt_dep.version:
                specs.append(opt_dep.version)

        res = ComponentWithVersions(requirement.name, [])
        for storage_client in _clients:
            try:
                for spec in specs:
                    new_res = storage_client.versions(component_name=requirement.name, spec=spec)

                    # solve resolution here. for resolution=latest we need to keep one for each spec
                    # to make sure the spec is solvable
                    prerelease_versions, stable_versions = [], []
                    for version in new_res.versions:
                        if Version(version.version).prerelease:
                            prerelease_versions.append(version)
                        else:
                            stable_versions.append(version)

                    if prerelease_versions and not stable_versions:
                        warn('No stable versions found. Using pre-release versions.')
                        version_group = prerelease_versions
                    else:
                        version_group = stable_versions

                    if resolution == VersionSolverResolution.LATEST:
                        new_res.versions = [version_group[0]] if version_group else []
                    else:
                        new_res.versions = version_group

                    res.merge(new_res)
            except (
                VersionNotFound,
                ComponentNotFound,
            ) as err:
                error_message += str(err)
            else:
                if res.versions:
                    return res, storage_client.storage_url

        raise VersionNotFound(error_message)
