import filecmp
import os
from collections import OrderedDict

import pytest

from component_manager.component_sources.idf import IDFSource
from component_manager.component_sources.web_service import WebServiceSource
from component_manager.lock.manager import LockManager
from component_manager.manifest import ComponentVersion
from component_manager.manifest_builder import ManifestBuilder
from component_manager.manifest_pipeline import ManifestParser
from component_manager.version_solver.solver_result import SolvedComponent, SolverResult

dependencies = OrderedDict(
    [
        ('idf', OrderedDict([('version', '4.4.4')])),
        (
            'test_cmp',
            OrderedDict(
                [
                    ('version', '1.2.7'),
                    (
                        'component_hash',
                        'f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b',
                    ),
                    (
                        'source',
                        OrderedDict([
                            ('service_url', 'https://repo.example.com'),
                            ('type', 'service'),
                        ]),
                    ),
                ]),
        ),
    ])
manifest_hash = 'f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b'
valid_lock_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'manifests',
    'dependencies.lock',
)
manifest_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'manifests',
    'valid_idf_project.yml',
)


class TestLockManager(object):
    def test_load_valid_lock(self):
        lock_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'manifests',
            'dependencies.lock',
        )
        parser = LockManager(lock_path)

        lock = parser.load()

        assert lock['component_manager_version'] == '0.0.1'
        assert (lock['dependencies']['test_cmp']['source']['service_url'] == 'https://repo.example.com')

    def test_load_invalid_lock(self, capsys):
        lock_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'manifests',
            'invalid_dependencies.lock',
        )
        parser = LockManager(lock_path)

        with pytest.raises(SystemExit) as e:
            parser.load()

        captured = capsys.readouterr()
        assert e.type == SystemExit
        assert e.value.code == 1
        assert captured.out.startswith('Error')

    def test_lock_dump_with_solution(self, tmp_path):
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        lock = LockManager(lock_path)
        mparser = ManifestParser(manifest_path).prepare()
        manifest = ManifestBuilder(mparser.manifest_tree).build()
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
        solution = SolverResult(manifest, components).as_ordered_dict()

        lock.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    @pytest.fixture(scope='session')
    def test_lock_dump_with_dictionary(self, tmp_path):
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        parser = LockManager(lock_path)
        solution = OrderedDict(
            [
                ('component_manager_version', '1.0.3'),
                ('dependencies', dependencies),
                ('manifest_hash', manifest_hash),
            ])

        parser.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    @pytest.fixture(scope='session')
    def test_lock_dump(self, tmp_path):
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        parser = LockManager(lock_path)
        solution = parser.load()
        solution['component_manager_version'] = '0.0.1'
        solution['manifest_hash'] = manifest_hash
        solution['dependencies'] = dependencies

        parser.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)
