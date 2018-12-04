from .solver_result import SolvedComponent, SolverResult


class VersionSolver(object):
    """
    The version solver that finds a set of package versions 
    that satisfy the root package's dependencies.
    """

    def __init__(self, manifest, locked=None):
        """Expects project manifest and optional dict of locked components"""
        self._manifest = manifest
        self.locked = locked

    @property
    def manifest(self):
        return self._manifest

    def solve(self):
        # TODO: implement real solving, now it will fail on any collision
        # TODO: fetch full tree of dependencies, now it fetches only direct dependencies
        # Thats a quick stub that always installs latest version
        solved_components = map(
            lambda component: SolvedComponent(
                name=component.name,
                version=max(
                    component.source.versions(
                        name=component.name, spec=component.version_spec
                    )
                ),
                source=component.source,
            ),
            self.manifest.dependencies,
        )

        return SolverResult(self.manifest, solved_components)
