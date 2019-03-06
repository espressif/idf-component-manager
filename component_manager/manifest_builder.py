from semantic_version import Version

from .component_sources import SourceBuilder
from .manifest import ComponentRequirement, Manifest


class ManifestBuilder(object):
    """Builds manifest object from manifest tree"""

    def __init__(self, manifest_tree):
        self.manifest_tree = manifest_tree

    def build(self):
        tree = self.manifest_tree
        manifest = Manifest(
            name=tree.get("name", None), maintainers=tree.get("maintainers", None)
        )
        version = tree.get("version", None)
        if version:
            manifest.version = Version(version)

        for name, details in tree.get("dependencies", {}).items():
            source = SourceBuilder(name, details).build()
            component = ComponentRequirement(
                name, source, version_spec=details["version"]
            )
            manifest.dependencies.append(component)

        return manifest
