"""Classes to work with manifest file"""
from semantic_version import Version


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


class ComponentRequirement(object):
    def __init__(self, name, source, versions=None, version_spec="*"):
        self.version_spec = version_spec
        self.source = source
        self.name = name.lower()


class ComponentVersion(object):
    def __init__(self, version, url_or_path=None):
        self.version = version if isinstance(version, Version) else Version(version)
        self.url_or_path = url_or_path


class ComponentWithVersions(object):
    def __init__(self, name, versions):
        self.versions = versions
        self.name = name.lower()  # Use only lower-case names internally
