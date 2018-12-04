from .version_solver import VersionSolver


def resolve_versions(manifest, locked=None):
    solver = VersionSolver(manifest, locked=locked)

    return solver.solve()
