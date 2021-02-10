import os

from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import SolvedComponent
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
        solution = manager.load()

        assert manager.exists()
        assert len(solution.dependencies) == 2
        cmp = solution.dependencies[0]
        assert isinstance(cmp, SolvedComponent)
        assert isinstance(cmp.source, WebServiceSource)
        assert cmp.source.base_url == 'https://repo.example.com'
        assert str(solution.dependencies[1].version) == '4.4.4'
