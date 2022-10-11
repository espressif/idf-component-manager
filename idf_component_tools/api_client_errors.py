# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


class APIClientError(Exception):
    pass


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


KNOWN_API_ERRORS = {
    'NamespaceNotFoundError': NamespaceNotFound,
    'ComponentNotFoundError': ComponentNotFound,
}
