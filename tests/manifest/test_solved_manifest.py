import os

from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import Manifest, SolvedComponent, SolvedManifest
from idf_component_tools.sources import WebServiceSource

valid_lock_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    '..',
    'fixtures',
    'locks',
    'dependencies.lock',
)


class TestSolverResult(object):
    def test_load_valid_lock(self):
        manager = LockManager(valid_lock_path)
        lock = manager.load()

        solution = SolvedManifest.fromdict(Manifest(), lock)

        assert manager.exists()
        assert len(solution.solved_components) == 2
        assert solution.solved_components[0].version == '4.4.4'
        cmp = solution.solved_components[1]
        assert isinstance(cmp, SolvedComponent)
        assert isinstance(cmp.source, WebServiceSource)
        assert cmp.source.base_url == 'https://repo.example.com'
