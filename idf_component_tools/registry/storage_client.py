# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t
from functools import wraps

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

    def component(self, component_name: str, version: t.Optional[str] = None) -> t.Dict[str, t.Any]:
        """
        Manifest for given version of component, if version is None highest version is returned
        Rewrites all urls to storage urls
        """
        component_name = component_name.lower()
        version = version or '*'

        component_response = self.get_component_response(component_name=component_name)
        filtered_versions = filter_versions(component_response.versions, version, component_name)
        if not filtered_versions:
            raise VersionNotFound(
                f'Version of the component "{component_name}" satisfying the spec "{version}" was not found.'
            )

        best_version = filtered_versions[0].model_dump()
        best_version['name'] = component_name

        best_version['download_url'] = join_url(self.storage_url, best_version['url'])
        best_version['checksums_url'] = join_url(self.storage_url, best_version['checksums'])

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
    def get_component_json(self, request: t.Callable, component_name: str) -> t.Dict:
        return request('get', ['components', component_name])

    @_request
    def get_component_response(
        self, request: t.Callable, component_name: str, spec: str = '*'
    ) -> ComponentResponse:
        try:
            return super().get_component_response(
                request=request, component_name=component_name, spec=spec
            )
        except StorageFileNotFound:
            raise ComponentNotFound(f'Component "{component_name}" not found')
