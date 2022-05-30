import os

from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import ManifestManager, SolvedComponent
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

    def test_solve_optional_dependency(self, monkeypatch, release_component_path):
        monkeypatch.setenv('IDF_VERSION', '5.0.0')
        monkeypatch.setenv('IDF_TARGET', 'esp32')

        manifest_manager = ManifestManager(release_component_path, 'test')
        manifest_manager.manifest_tree['dependencies'] = {
            'test': '1.2.3',
            'pest': {
                'version': '3.2.1'
            },
            'foo': {
                'version': '1.0.0',
                'rules': [
                    {
                        'if': 'idf_version == 5.0.0'
                    },
                    {
                        'if': 'target not in [esp32, esp32c3]'
                    },
                ]
            }
        }
        manifest = manifest_manager.load()
        assert len(manifest.dependencies) == 2
        assert manifest.dependencies[0].name == 'espressif/pest'
        assert manifest.dependencies[1].name == 'espressif/test'
