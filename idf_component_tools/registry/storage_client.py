# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t
from functools import wraps

from schema import Schema

import idf_component_tools as tools
from idf_component_tools.manifest import ComponentWithVersions, HashedComponentVersion
from idf_component_tools.registry.api_client_errors import (
    ComponentNotFound,
    StorageFileNotFound,
    VersionNotFound,
)
from idf_component_tools.registry.api_schemas import COMPONENT_SCHEMA
from idf_component_tools.registry.base_client import BaseClient, create_session, filter_versions
from idf_component_tools.registry.component_details import ComponentDetailsWithStorageURL
from idf_component_tools.registry.request_processor import base_request, join_url
from idf_component_tools.semver import SimpleSpec, Version


class ComponentWithVersionsAndStorageURL(ComponentWithVersions):
    def __init__(
        self, name: str, versions: t.List[HashedComponentVersion], storage_url: t.Optional[str]
    ) -> None:
        super().__init__(name, versions)
        self.storage_url = storage_url

    @classmethod
    def from_component_with_versions(cls, cmp_with_versions, storage_url):
        return cls(cmp_with_versions.name, cmp_with_versions.versions, storage_url)


class StorageClient(BaseClient):
    def __init__(self, storage_url=None, sources=None):
        super().__init__(sources)
        self.storage_url = storage_url

    def _request(cache: t.Union[BaseClient, bool] = False) -> t.Callable:
        def decorator(f: t.Callable[..., t.Any]) -> t.Callable:
            @wraps(f)  # type: ignore
            def wrapper(self, *args, **kwargs):
                url = self.storage_url
                session = create_session(cache=cache)

                def request(
                    method: str,
                    path: t.List[str],
                    data: t.Optional[t.Dict] = None,
                    json: t.Optional[t.Dict] = None,
                    headers: t.Optional[t.Dict] = None,
                    schema: t.Optional[Schema] = None,
                ):
                    path[-1] += '.json'
                    return base_request(
                        url,
                        session,
                        method,
                        path,
                        data=data,
                        json=json,
                        headers=headers,
                        schema=schema,
                        use_storage=True,
                    )

                return f(self, request=request, *args, **kwargs)

            return wrapper

        return decorator

    @_request(cache=True)
    def versions(
        self, request: t.Callable, component_name: str, spec: str = '*'
    ) -> ComponentWithVersionsAndStorageURL:
        """List of versions for given component with required spec"""
        try:
            cmp_with_versions = super().versions(
                request=request, component_name=component_name, spec=spec
            )
        except StorageFileNotFound:
            raise ComponentNotFound(f'Component "{component_name}" not found')

        return ComponentWithVersionsAndStorageURL.from_component_with_versions(
            cmp_with_versions, self.storage_url
        )

    def component(
        self, component_name: str, version: t.Optional[str] = None
    ) -> ComponentDetailsWithStorageURL:
        """
        Manifest for given version of component, if version is None highest version is returned
        """

        component_name = component_name.lower()
        info = self.get_component_info(component_name=component_name)

        versions = info['versions']
        filtered_versions = filter_versions(versions, version, component_name)

        if not filtered_versions:
            raise VersionNotFound(
                'Version of the component "{}" satisfying the spec "{}" was not found.'.format(
                    component_name, str(version)
                )
            )

        best_version = max(filtered_versions, key=lambda v: Version(v['version']))
        download_url = join_url(self.storage_url, best_version['url'])

        documents = best_version['docs']
        for document, url in documents.items():
            documents[document] = join_url(self.storage_url, url)

        license_info = best_version['license']
        license_name = None
        license_url = None
        if license_info:
            license_name = license_info['name']
            license_url = join_url(self.storage_url, license_info['url'])

        examples = best_version['examples']
        for example in examples:
            example.update({'url': join_url(self.storage_url, example['url'])})

        return ComponentDetailsWithStorageURL(
            name=f"{info['namespace']}/{info['name']}",
            version=tools.manifest.ComponentVersion(best_version['version']),
            dependencies=self.version_dependencies(best_version),
            maintainers=None,
            download_url=download_url,
            documents=documents,
            license_name=license_name,
            license_url=license_url,
            examples=examples,
            storage_url=self.storage_url,
        )

    @_request(cache=True)
    def get_component_info(
        self, request: t.Callable, component_name: str, spec: str = '*'
    ) -> t.Dict:
        try:
            response = request(
                'get', ['components', component_name.lower()], schema=COMPONENT_SCHEMA
            )
        except StorageFileNotFound:
            raise ComponentNotFound(f'Component "{component_name}" not found')

        if spec != '*':
            versions = []
            for version in response['versions']:
                if not SimpleSpec(spec).match(Version(version['version'])):
                    continue
                versions.append(version)

            response['versions'] = versions

        return response
