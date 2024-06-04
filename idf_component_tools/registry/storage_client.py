# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t
from functools import wraps

from idf_component_tools.semver import SimpleSpec, Version
from idf_component_tools.utils import (
    ComponentWithVersions,
)

from .api_models import ApiBaseModel, ComponentResponse
from .base_client import BaseClient, create_session, filter_versions
from .client_errors import ComponentNotFound, StorageFileNotFound, VersionNotFound
from .request_processor import base_request, join_url


class StorageClient(BaseClient):
    def __init__(self, storage_url: str, default_namespace: t.Optional[str] = None) -> None:
        super().__init__(default_namespace=default_namespace)

        self.storage_url = storage_url

    def _request(f: t.Callable[..., t.Any]) -> t.Callable:  # type: ignore
        @wraps(f)  # type: ignore
        def wrapper(self, *args, **kwargs):
            session = create_session()

            def request(
                method: str,
                path: t.List[str],
                data: t.Optional[t.Dict] = None,
                json: t.Optional[t.Dict] = None,
                headers: t.Optional[t.Dict] = None,
                schema: t.Optional[ApiBaseModel] = None,
            ):
                path[-1] += '.json'
                return base_request(
                    self.storage_url,
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

    @_request
    def versions(
        self, request: t.Callable, component_name: str, spec: str = '*', **kwargs
    ) -> ComponentWithVersions:
        """List of versions for given component with required spec"""
        try:
            cmp_with_versions = super().versions(
                request=request,
                component_name=component_name,
                spec=spec,
                **kwargs,
            )
        except StorageFileNotFound:
            raise ComponentNotFound(f'Component "{component_name}" not found')

        return cmp_with_versions

    def component(self, component_name: str, version: t.Optional[str] = None) -> t.Dict[str, t.Any]:
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

        best_version['name'] = component_name

        best_version['download_url'] = join_url(self.storage_url, best_version['url'])

        documents = best_version['docs']
        for document, url in documents.items():
            documents[document] = join_url(self.storage_url, url)

        license_info = best_version['license']
        if license_info:
            license_info['url'] = join_url(self.storage_url, license_info['url'])

        examples = best_version['examples']
        for example in examples:
            example.update({'url': join_url(self.storage_url, example['url'])})

        return best_version

    @_request
    def get_component_info(
        self, request: t.Callable, component_name: str, spec: str = '*'
    ) -> t.Dict:
        try:
            response = request(
                'get', ['components', component_name.lower()], schema=ComponentResponse
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
