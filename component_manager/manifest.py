"""Classes to work with manifest file"""


class Manifest(object):
    def __init__(
        self, name=None, version=None, maintainers=None, dependencies=None, url=None
    ):
        self.name = str(name).lower()  # Use only lower-case names internally
        self.version = version
        self.maintainers = maintainers
        if dependencies is None:
            dependencies = []
        self.dependencies = dependencies
        self.url = url


class Component(object):
    def __init__(self, name, source, versions=None, version_spec="*"):
        self.version_spec = version_spec
        self.source = source
        self.name = name.lower()
