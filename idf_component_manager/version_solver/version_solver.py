from typing import Optional

from idf_component_tools.manifest import ComponentRequirement, ProjectRequirements, SolvedComponent, SolvedManifest


class VersionSolver(object):
    """
    The version solver that finds a set of package versions
    that satisfy the root package's dependencies.
    """
    def __init__(
            self, requirements, old_solution=None):  # type: (ProjectRequirements, Optional[SolvedManifest]) -> None
        """Expects project manifest and optional old solution"""
        self.requirements = requirements
        self.old_solution = old_solution

    def solve(self):
        # TODO: implement real solving, now it ignores collisions
        # TODO: solve recursively
        def best_version(component):  # type: (ComponentRequirement) -> SolvedComponent
            cmp_with_versions = component.source.versions(name=component.name, spec=component.version_spec)
            version = max(cmp_with_versions.versions)
            return SolvedComponent(
                name=component.name, source=component.source, version=version, component_hash=version.component_hash)

        solved_components = {}
        for manifest in self.requirements.manifests:
            for dependency in manifest.dependencies:
                solved_components[dependency.name] = best_version(dependency)

        return SolvedManifest(list(solved_components.values()), self.requirements.manifest_hash)
