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

MANIFEST_HASH = '145601a909ff39faf9fc846504dedd90b6c0ee311d401b70e4c3aef00bd454b9'
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

        test_cmp = [cmp for cmp in lock.dependencies if cmp.name == 'test_cmp'][0]
        assert (test_cmp.source.service_url == 'https://repo.example.com')

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

        solution = SolvedManifest(components, manifest_hash=manifest.manifest_hash)
        lock.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    def test_lock_dump_with_dictionary(self, tmp_path):
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        parser = LockManager(lock_path)
        solution = SolvedManifest.fromdict(
            dict([
                ('version', '1.0.0'),
                ('dependencies', dependencies),
                ('manifest_hash', MANIFEST_HASH),
            ]))

        parser.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    def test_lock_dump(self, tmp_path):
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        parser = LockManager(lock_path)
        solution = parser.load()
        solution.manifest_hash = MANIFEST_HASH
        for (name, details) in dependencies.items():
            details['name'] = name
            solution.dependencies.append(SolvedComponent.fromdict(details))

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
