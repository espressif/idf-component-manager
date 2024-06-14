# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Classes to work with ESP Component Registry"""

import os
import typing as t
from functools import wraps
from ssl import SSLEOFError

from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

from idf_component_tools.utils import ComponentWithVersions

from .api_models import (
    ApiBaseModel,
    ApiInformation,
    ApiToken,
    TaskStatus,
    VersionUpload,
)
from .base_client import BaseClient, create_session
from .client_errors import APIClientError, ContentTooLargeError, NoRegistrySet
from .request_processor import base_request


def auth_required(f: t.Callable) -> t.Callable:
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if not self.api_token:
            raise APIClientError('API token is required')
        return f(self, *args, **kwargs)

    return wrapper


class APIClient(BaseClient):
    def __init__(
        self,
        registry_url: t.Optional[str] = None,
        api_token: t.Optional[str] = None,
        default_namespace: t.Optional[str] = None,
    ) -> None:
        super().__init__(default_namespace=default_namespace)

        self.registry_url = registry_url
        self.api_token = api_token

    def _request(f: t.Callable[..., t.Any]) -> t.Callable:  # type: ignore
        @wraps(f)  # type: ignore
        def wrapper(self, *args, **kwargs):
            if not self.registry_url:
                raise NoRegistrySet(
                    'The current operation requires access to the IDF component registry. '
                    'However, the registry URL is not set. You can set the '
                    'IDF_COMPONENT_REGISTRY_URL environment variable or "registry_url" field '
                    'for your current profile in "idf_component_manager.yml" file. '
                    'To use the default IDF component registry '
                    'unset IDF_COMPONENT_STORAGE_URL environment variable or remove '
                    '"storage_url" field from the "idf_component_manager.yml" file'
                )

            session = create_session(token=self.api_token)

            def request(
                method: str,
                path: t.List[str],
                data: t.Optional[t.Dict] = None,
                json: t.Optional[t.Dict] = None,
                headers: t.Optional[t.Dict] = None,
                schema: t.Optional[ApiBaseModel] = None,
            ):
                # always access '<registry_url>/api' while doing api calls
                path = ['api', *path]

                return base_request(
                    self.registry_url,
                    session,
                    method,
                    path,
                    data=data,
                    json=json,
                    headers=headers,
                    schema=schema,
                )

            return f(self, request=request, *args, **kwargs)

        return wrapper

    @_request
    def api_information(self, request: t.Callable) -> t.Dict:
        """Get information about API status, including storage URL"""
        return request('get', [], schema=ApiInformation)

    @auth_required
    @_request
    def token_information(self, request: t.Callable) -> t.Dict:
        """Get information about current token"""
        return request('get', ['tokens', 'current'], schema=ApiToken)

    @auth_required
    @_request
    def revoke_current_token(self, request: t.Callable) -> None:
        """Revoke current token"""
        request('delete', ['tokens', 'current'])

    def _upload_version_to_endpoint(self, request, file_path, endpoint, callback=None):
        with open(file_path, 'rb') as file:
            filename = os.path.basename(file_path)

            encoder = MultipartEncoder({'file': (filename, file, 'application/octet-stream')})
            headers = {'Content-Type': encoder.content_type}
            data = MultipartEncoderMonitor(encoder, callback)

            try:
                return request(
                    'post',
                    endpoint,
                    data=data,
                    headers=headers,
                    schema=VersionUpload,
                )['job_id']
            # Python 3.10+ can't process 413 error - https://github.com/urllib3/urllib3/issues/2733
            except (SSLEOFError, ContentTooLargeError):
                raise APIClientError(
                    'The component archive exceeds the maximum allowed size. Please consider '
                    'excluding unnecessary files from your component. If you think your component '
                    'should be uploaded as it is, please contact components@espressif.com'
                )

    @_request
    def versions(
        self, request: t.Callable, component_name: str, spec: str = '*'
    ) -> ComponentWithVersions:
        """List of versions for given component with required spec"""
        return super().versions(request=request, component_name=component_name, spec=spec)

    @auth_required
    @_request
    def upload_version(self, request, component_name, file_path, callback=None):
        return self._upload_version_to_endpoint(
            request,
            file_path,
            ['components', component_name.lower(), 'versions'],
            callback,
        )

    @_request
    def validate_version(self, request, file_path, callback=None):
        return self._upload_version_to_endpoint(
            request, file_path, ['components', 'validate'], callback
        )

    @auth_required
    @_request
    def delete_version(
        self,
        request: t.Callable,
        component_name: str,
        component_version: str,
    ) -> None:
        request('delete', ['components', component_name.lower(), component_version])

    @auth_required
    @_request
    def yank_version(
        self,
        request: t.Callable,
        component_name: str,
        component_version: str,
        yank_message: str,
    ) -> None:
        request(
            'post',
            ['components', component_name.lower(), component_version, 'yank'],
            json={'message': yank_message},
        )

    @_request
    def task_status(self, request: t.Callable, job_id: str) -> TaskStatus:
        return TaskStatus.model_validate(request('get', ['tasks', job_id]))
