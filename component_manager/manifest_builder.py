from strictyaml import Any

from component_management_tools.hash_tools import hash_object
from component_manager.manifest import ComponentVersion

from .component_sources.builder import SourceBuilder
from .manifest import ComponentRequirement, Manifest


class ManifestBuilder(object):
    """Coverts manifest dict to manifest object"""
    def __init__(self, manifest_tree):  # type: (Any) -> None
        self.manifest_tree = manifest_tree

    def build(self):  # type: () -> Manifest
        tree = self.manifest_tree
        manifest = Manifest(
            name=tree.get('name', None),
            maintainers=tree.get('maintainers', None),
            manifest_hash=hash_object(dict(tree)))
        version = tree.get('version', None)

        if version:
            manifest.version = ComponentVersion(version)

        for name, details in tree.get('dependencies', {}).items():
            source = SourceBuilder(name, details).build()
            # Add all extra fields from requirements, excluding version
            source_specific_options = {}
            for (key, value) in details.items():
                if key in source.known_keys() and key != 'version':
                    source_specific_options[key] = value

            component = ComponentRequirement(
                name, source, version_spec=details.get('version', '*'), source_specific_options=source_specific_options)
            manifest.dependencies.append(component)

        return manifest
