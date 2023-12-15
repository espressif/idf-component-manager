# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client  # type: ignore

try:
    from typing import Any
except ImportError:
    pass


class APIClientError(Exception):
    def __init__(self, message='API Request Error', endpoint=None, status_code=None):
        # type: (Any, str | None, int | None) -> None
        super(APIClientError, self).__init__(message)
        self.endpoint = endpoint
        self.status_code = status_code

    def request_info(self):  # type: () -> list[str]
        messages = []
        if self.endpoint is not None:
            messages.append('URL: {}'.format(self.endpoint))

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
