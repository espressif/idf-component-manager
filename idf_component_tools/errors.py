# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import warnings

try:
    from typing import Any
except ImportError:
    pass


class UserHint(Warning):
    pass


class UserDeprecationWarning(UserWarning):
    pass


def warn(message):  # type: (Exception | str) -> None
    warnings.warn(str(message))


def hint(message):  # type: (Exception | str) -> None
    warnings.warn(str(message), category=UserHint)


class FatalError(RuntimeError):
    """Generic unrecoverable runtime error"""
    exit_code = 2

    def __init__(self, *args, **kwargs):  # type: (Any, Any) -> None
        super(FatalError, self).__init__(*args)
        exit_code = kwargs.pop('exit_code', None)
        if exit_code:
            self.exit_code = exit_code


class NothingToDoError(FatalError):
    '''Generic Runtime error for states when operation is prematurely aborted due to nothing to do'''
    exit_code = 144  # NOP


class SolverError(FatalError):
    pass


class DependencySolveError(FatalError):
    def __init__(self, *args, **kwargs):
        super(FatalError, self).__init__(*args)
        if 'dependency' not in kwargs:
            raise ValueError('"dependency" keyword must be used in "DependencySolverError"')

        self.dependency = kwargs.pop('dependency')
        self.spec = kwargs.pop('spec', None)


class ProcessingError(FatalError):
    pass


class FetchingError(ProcessingError):
    pass


class SourceError(ProcessingError):
    pass


class ManifestError(ProcessingError):
    pass


class LockError(ProcessingError):
    pass


class GitError(ProcessingError):
    pass


class ComponentModifiedError(ProcessingError):
    pass


class InvalidComponentHashError(ProcessingError):
    pass
