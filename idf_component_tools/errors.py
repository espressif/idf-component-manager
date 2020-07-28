class FatalError(RuntimeError):
    """
    Wrapper class for unrecoverable runtime errors.
    """
    pass


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
