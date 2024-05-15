# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import http.client as http_client
import typing as t


class APIClientError(Exception):
    def __init__(
        self,
        message: t.Any = 'API Request Error',
        endpoint: t.Optional[str] = None,
        status_code: t.Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.endpoint = endpoint
        self.status_code = status_code

    def request_info(self) -> t.List[str]:
        messages = []
        if self.endpoint is not None:
            messages.append(f'URL: {self.endpoint}')

        if self.status_code is not None:
            messages.append(
                'Status code: {} {}'.format(
                    self.status_code, http_client.responses.get(self.status_code, '')
                )
            )

        return messages


class NetworkConnectionError(APIClientError):
    pass


class ComponentNotFound(APIClientError):
    pass


class NamespaceNotFound(APIClientError):
    pass


class VersionNotFound(APIClientError):
    pass


class StorageFileNotFound(APIClientError):
    pass


class NoRegistrySet(APIClientError):
    pass


class ContentTooLargeError(APIClientError):
    pass


KNOWN_API_ERRORS = {
    'NamespaceNotFoundError': NamespaceNotFound,
    'ComponentNotFoundError': ComponentNotFound,
    'VersionNotFoundError': VersionNotFound,
}
