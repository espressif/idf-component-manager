from typing import List, Union

from semantic_version import Version
from strictyaml import Any

from .component_sources import BaseSource, SourceBuilder
from .lock.hash_tools import HashTools
from .manifest import ComponentRequirement, Manifest


class ManifestBuilder(object):
    """Coverts manifest dict to manifest object"""

    def __init__(self, manifest_tree, sources=None):  # type: (Any, Union[List[BaseSource], None] ) -> None
        self.manifest_tree = manifest_tree

        if sources is None:
            sources = []
        self.sources = sources

    def build(self):  # type: () -> Manifest
        tree = self.manifest_tree
        manifest = Manifest(name=tree.get('name', None),
                            maintainers=tree.get('maintainers', None),
                            manifest_hash=HashTools.hash_object(dict(tree)))
        version = tree.get('version', None)

        if version:
            manifest.version = Version(version)

        for name, details in tree.get('dependencies', {}).items():
            source = SourceBuilder(name, details).build()
            component = ComponentRequirement(name, source, version_spec=details.get('version', '*'))
            manifest.dependencies.append(component)

        return manifest
