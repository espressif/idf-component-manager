"""Results of the solver"""


class SolvedComponent(object):
    def __init__(self, name, version, source):
        self.name = name
        self.version = version
        self.source = source


class SolverResult(object):
    def __init__(self, manifest, solved_components):
        self._manifest = manifest
        self._solved_components = solved_components

    @property
    def solved_components(self):
        return self._solved_components

    @property
    def manifest(self):
        return self._manifest
