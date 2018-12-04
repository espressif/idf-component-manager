"""Classes to work with manifest file"""


class Manifest(object):
    def __init__(
        self,
        name=None,
        version=None,
        idf_version=None,
        maintainers=None,
        dependencies=None,
    ):
        self.name = str(name).lower()  # Use only lower-case names internally
        self.version = version
        # TODO: add idf_source and trait idf as a locked component (after implementation of fully featured solver)
        self.idf_version = idf_version
        self.maintainers = maintainers
        if dependencies is None:
            dependencies = []
        self.dependencies = dependencies


class Component(object):
    def __init__(self, name, source, versions=None, version_spec="*"):
        self.version_spec = version_spec
        self.source = source
        self.name = name.lower()
