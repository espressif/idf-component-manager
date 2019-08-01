import os

from component_manager.component_sources import WebServiceSource
from component_manager.lock.manager import LockManager
from component_manager.manifest import Manifest
from component_manager.version_solver.solver_result import (SolvedComponent, SolverResult)

valid_lock_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'manifests',
    'dependencies.lock',
)


class TestSolverResult(object):
    def test_load_valid_lock(self):
        lock = LockManager(valid_lock_path).load()

        solution = SolverResult.from_yaml(Manifest(), lock)

        assert len(solution.solved_components) == 2
        assert solution.solved_components[0].version == '4.4.4'
        cmp = solution.solved_components[1]
        assert isinstance(cmp, SolvedComponent)
        assert isinstance(cmp.source, WebServiceSource)
        assert cmp.source.base_url == 'https://repo.example.com'
