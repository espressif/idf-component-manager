# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
class ValidatingHashError(Exception):
    pass


class HashNotEqualError(ValidatingHashError):
    pass


class HashNotSHA256Error(ValidatingHashError):
    pass


class HashDoesNotExistError(ValidatingHashError):
    pass
