# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

# Validate hash errors


class ValidatingHashError(Exception):
    pass


class ComponentNotFoundError(ValidatingHashError):
    pass


class HashNotFoundError(ValidatingHashError):
    pass


class HashNotSHA256Error(ValidatingHashError):
    pass


class HashNotEqualError(ValidatingHashError):
    pass


class HashDictEmptyError(ValidatingHashError):
    pass


# Checksums parse errors


class ChecksumsParseError(Exception):
    pass


class ChecksumsInvalidJson(ChecksumsParseError):
    pass


class ChecksumsFileNotFound(ChecksumsParseError):
    pass


class ChecksumsUnsupportedVersion(ChecksumsParseError):
    pass


class ChecksumsUnsupportedAlgorithm(ChecksumsParseError):
    pass


class ChecksumsInvalidChecksum(ChecksumsParseError):
    pass
