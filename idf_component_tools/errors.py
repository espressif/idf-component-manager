# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


try:
    from typing import Any
except ImportError:
    pass


class FatalError(RuntimeError):
    """Generic unrecoverable runtime error"""

    exit_code = 2

    def __init__(self, *args, **kwargs):  # type: (Any, Any) -> None
        super(FatalError, self).__init__(*args)
        exit_code = kwargs.pop('exit_code', None)
        if exit_code:
            self.exit_code = exit_code


class InternalError(RuntimeError):
    """Internal Error, should report to us"""

    def __init__(self):
        super(InternalError, self).__init__(
            'This is an internal error. Please report on '
            '`https://github.com/espressif/idf-component-manager/issues '
            'with your operating system, idf-component-manager version, '
            'and the traceback log. Thanks for reporting! '
        )


class NothingToDoError(FatalError):
    '''Generic Runtime error for states when operation is prematurely
    aborted due to nothing to do'''

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


class MetadataError(ProcessingError):
    pass


class MetadataKeyError(ProcessingError):
    def __init__(self, field_name, field_type):
        super(MetadataKeyError, self).__init__(
            'Unknown {} field "{}" in the manifest file that may affect build result'.format(
                field_type, field_name
            )
        )


class LockError(ProcessingError):
    pass


class GitError(ProcessingError):
    pass


class ComponentModifiedError(ProcessingError):
    pass


class InvalidComponentHashError(ProcessingError):
    pass


class VersionNotFoundError(FatalError):
    pass


class VersionAlreadyExistsError(FatalError):
    pass


class ProfileNotValid(FatalError):
    pass
