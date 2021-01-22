import filecmp
import os

import pytest
from idf_component_tools.errors import LockError
from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import ComponentVersion, Manifest, ManifestManager, SolvedComponent, SolvedManifest
from idf_component_tools.sources import IDFSource, WebServiceSource

dependencies = {
    'idf': {
        'version': '4.4.4',
        'source': {
            'type': 'idf'
        }
    },
    'test_cmp': {
        'version': '1.2.7',
        'component_hash': 'f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b',
        'source': {
            'service_url': 'https://repo.example.com',
            'type': 'service'
        }
    }
}

manifest_hash = 'bd7763113fbae1930ae1cccb8a717d3f267523a923f80e69a3d33d9e912ac450'
valid_lock_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    'locks',
    'dependencies.lock',
)
manifest_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    'idf_component.yml',
)


class TestLockManager(object):
    def test_load_valid_lock(self):
        parser = LockManager(valid_lock_path)

        lock = parser.load()

        assert parser.exists()
        assert lock['version'] == '1.0.0'
        assert (lock['dependencies']['test_cmp']['source']['service_url'] == 'https://repo.example.com')

    def test_lock_dump_with_solution(self, tmp_path):
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        lock = LockManager(lock_path)
        tree = ManifestManager(manifest_path).load()
        manifest = Manifest.fromdict(tree)
        components = [
            SolvedComponent(
                name='idf',
                version=ComponentVersion('4.4.4'),
                source=IDFSource({}),
            ),
            SolvedComponent(
                name='test_cmp',
                version=ComponentVersion('1.2.7'),
                source=WebServiceSource({'service_url': 'https://repo.example.com'}),
                component_hash='f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b',
            ),
        ]

        solution = SolvedManifest(manifest, components)
        lock.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    def test_lock_dump_with_dictionary(self, tmp_path):
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        parser = LockManager(lock_path)
        solution = dict([
            ('version', '1.0.0'),
            ('dependencies', dependencies),
            ('manifest_hash', manifest_hash),
        ])

        parser.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    def test_lock_dump(self, tmp_path):
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        parser = LockManager(lock_path)
        solution = parser.load()
        solution['version'] = '1.0.0'
        solution['manifest_hash'] = manifest_hash
        solution['dependencies'] = dependencies

        parser.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    def test_load_invalid_lock(self, capsys):
        lock_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'fixtures',
            'locks',
            'invalid_dependencies.lock',
        )

        parser = LockManager(lock_path)
        assert parser.exists()

        with pytest.raises(LockError) as e:
            parser.load()

        assert e.type == LockError
