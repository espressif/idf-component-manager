# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


class APIClientError(Exception):
    pass


class ComponentNotFound(APIClientError):
    pass


class NamespaceNotFound(APIClientError):
    pass


KNOWN_API_ERRORS = {
    'NamespaceNotFoundError': NamespaceNotFound,
    'ComponentNotFoundError': ComponentNotFound,
}
