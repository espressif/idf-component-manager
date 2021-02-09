from idf_component_tools.manifest import ComponentRequirement, ProjectRequirements, SolvedComponent, SolvedManifest

try:
    from typing import Dict, Optional
except ImportError:
    pass


def best_version(component):  # type: (ComponentRequirement) -> SolvedComponent
    cmp_with_versions = component.source.versions(name=component.name, spec=component.version_spec)
    version = max(cmp_with_versions.versions)
    return SolvedComponent(
        name=component.name,
        source=component.source,
        version=version,
        component_hash=version.component_hash,
    )


def solve_manifest(requirements, solved_components):
    '''Simple solver, every component processed only once'''
    for requirement in requirements:
        if requirement.name in solved_components:
            continue

        component = best_version(requirement)
        solved_components[component.name] = component
        solve_manifest(component.version.dependencies, solved_components)


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

    def solve(self):  # type: () -> SolvedManifest
        solved_components = {}  # type: Dict[str, SolvedComponent]
        for manifest in self.requirements.manifests:
            solve_manifest(manifest.dependencies, solved_components)

        return SolvedManifest(list(solved_components.values()), self.requirements.manifest_hash)
