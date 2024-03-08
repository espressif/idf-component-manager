# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import filecmp
import os
import shutil
import textwrap
from pathlib import Path

import pytest
import requests
import requests_mock

from idf_component_manager.dependencies import is_solve_required
from idf_component_tools.build_system_tools import get_idf_version
from idf_component_tools.errors import LockError
from idf_component_tools.lock import EMPTY_LOCK, LockManager
from idf_component_tools.manifest import (
    ComponentVersion,
    Manifest,
    ManifestManager,
    ProjectRequirements,
)
from idf_component_tools.manifest.solved_component import SolvedComponent
from idf_component_tools.manifest.solved_manifest import SolvedManifest
from idf_component_tools.messages import UserHint
from idf_component_tools.sources import IDFSource, LocalSource, WebServiceSource

dependencies = {
    'idf': {'version': '4.4.4', 'source': {'type': 'idf'}},
    'espressif/test_cmp': {
        'version': '1.2.7',
        'component_hash': 'f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b',
        'source': {'service_url': 'https://repo.example.com', 'type': 'service'},
    },
}

MANIFEST_HASH = 'a1a5f092fd8e895c42e8bb1984c5b32b86c49e796369605ca175edb079407f77'


@pytest.fixture
def valid_lock_path(fixtures_path):
    return os.path.join(
        fixtures_path,
        'locks',
        'dependencies.lock',
    )


@pytest.fixture
def manifest_path(fixtures_path):
    return os.path.join(
        fixtures_path,
        'idf_component.yml',
    )


@pytest.fixture
def connection_error_request():
    with requests_mock.Mocker() as m:
        m.register_uri(
            requests_mock.ANY, requests_mock.ANY, exc=requests.exceptions.ConnectionError
        )
        yield m


class TestLockManager:
    def test_load_valid_lock(self, valid_lock_path):
        parser = LockManager(valid_lock_path)

        lock = parser.load()
        assert parser.exists()

        test_cmp = [cmp for cmp in lock.dependencies if cmp.name == 'espressif/test_cmp'][0]
        assert test_cmp.source.service_url == 'https://repo.example.com'

    def test_lock_dump_with_solution(self, tmp_path, monkeypatch, manifest_path, valid_lock_path):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')

        lock = LockManager(lock_path)
        manifest = ManifestManager(manifest_path, name='test').load()
        components = [
            SolvedComponent(
                name='idf',
                version=ComponentVersion('4.4.4'),
                source=IDFSource({}),
            ),
            SolvedComponent(
                name='espressif/test_cmp',
                version=ComponentVersion('1.2.7'),
                source=WebServiceSource({'service_url': 'https://repo.example.com'}),
                component_hash='f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b',
            ),
        ]

        solution = SolvedManifest(components, manifest_hash=manifest.manifest_hash)
        lock.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    def test_lock_dump_with_dictionary(self, tmp_path, monkeypatch, valid_lock_path):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        parser = LockManager(lock_path)
        solution = SolvedManifest.fromdict(
            dict([
                ('version', '1.0.0'),
                ('dependencies', dependencies),
                ('manifest_hash', MANIFEST_HASH),
            ])
        )

        parser.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    def test_lock_dump(self, tmp_path, monkeypatch, valid_lock_path):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        parser = LockManager(lock_path)
        solution = parser.load()
        solution.manifest_hash = MANIFEST_HASH
        for name, details in dependencies.items():
            details['name'] = name
            solution.dependencies.append(SolvedComponent.fromdict(details))

        parser.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    def test_load_invalid_lock(self, monkeypatch, fixtures_path):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        lock_path = os.path.join(
            fixtures_path,
            'locks',
            'invalid_dependencies.lock',
        )

        parser = LockManager(lock_path)
        assert parser.exists()

        with pytest.raises(LockError) as e:
            parser.load()

        assert e.type == LockError

    def test_minimal_lock(self, tmp_path, monkeypatch):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        monkeypatch.setenv('IDF_VERSION', '5.1.0')
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        parser = LockManager(lock_path)
        solution = SolvedManifest.fromdict({
            'version': '1.0.0',
            'manifest_hash': MANIFEST_HASH,
            'dependencies': {
                'idf': {
                    'component_hash': None,
                    'source': {
                        'type': 'idf',
                    },
                    'version': get_idf_version(),
                }
            },
        })

        parser.dump(solution)
        loaded_solution = parser.load()

        assert solution.manifest_hash == loaded_solution.manifest_hash

        file_str = (
            textwrap.dedent(
                """
            dependencies:
              idf:
                component_hash: null
                source:
                  type: idf
                version: 5.1.0
            manifest_hash: {}
            target: esp32
            version: 1.0.0
        """
            )
            .format(solution.manifest_hash)
            .strip()
        )

        with open(lock_path) as f:
            assert f.read().strip() == file_str

    def test_empty_lock_file(self, tmp_path):
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        Path(lock_path).touch()

        solution = LockManager(lock_path).load()

        assert solution.manifest_hash is None

    def test_no_internet_connection(self, capsys, connection_error_request):
        manifest = Manifest.fromdict({'dependencies': {'idf': '4.4.0'}}, name='test_manifest')
        project_requirements = ProjectRequirements([manifest])
        solution = SolvedManifest.fromdict(
            dict([
                ('version', '1.0.0'),
                (
                    'dependencies',
                    {
                        'example/cmp': {
                            'component_hash': '8644358a11a35a986b0ce4d325ba3d1aa9491b9518111acd4ea9447f11dc47c1',  # noqa
                            'source': {
                                'service_url': 'https://ohnoIdonthaveinternetconnection.com',
                                'type': 'service',
                            },
                            'version': '3.3.7',
                        },
                    },
                ),
                (
                    'manifest_hash',
                    'cfedb62005f55b7e817bb733bb4d5df5047267a0229a162d4904ca9869af1522',
                ),
            ])
        )

        with pytest.warns(UserHint) as record:
            assert not is_solve_required(project_requirements, solution)
            assert (
                'Cannot establish a connection to the component registry. '
                'Skipping checks of dependency changes.' in record.list[0].message.args[0]
            )

    def test_change_manifest_file_idf_version(self, monkeypatch, capsys):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        manifest = Manifest.fromdict({'dependencies': {'idf': '4.4.0'}}, name='test_manifest')
        project_requirements = ProjectRequirements([manifest])
        solution = SolvedManifest.fromdict(
            dict([
                ('version', '1.0.0'),
                (
                    'dependencies',
                    {
                        'idf': {
                            'component_hash': None,
                            'source': {'type': 'idf'},
                            'version': '4.2.0',
                        }
                    },
                ),
                (
                    'manifest_hash',
                    '501e298399139355647b9d36da3bc3234eb14eb8b128e84e0548035e01c5b98f',
                ),
            ])
        )

        monkeypatch.setenv('IDF_VERSION', '4.4.0')
        assert is_solve_required(project_requirements, solution)  # Different idf version
        captured = capsys.readouterr()

        solution.manifest_hash = 'bff084ca418bd07bbb3f7b0a6713f45e802be72a006a5f30ac70ac755639683c'
        assert is_solve_required(project_requirements, solution)  # Wrong manifest hash
        captured = capsys.readouterr()
        assert 'Manifest files have changed, solving dependencies' in captured.out

        monkeypatch.setenv('IDF_VERSION', '4.2.0')
        solution.manifest_hash = 'cfedb62005f55b7e817bb733bb4d5df5047267a0229a162d4904ca9869af1522'
        assert not is_solve_required(project_requirements, solution)
        captured = capsys.readouterr()
        assert 'solving dependencies.' not in captured.out

    def test_change_manifest_file_dependencies_rules(
        self, monkeypatch, capsys, release_component_path
    ):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        monkeypatch.setenv('IDF_VERSION', '4.4.0')
        manifest_dict = {
            'dependencies': {
                'foo': {
                    'version': '*',
                    'rules': [
                        {'if': 'idf_version > 4'},
                    ],
                }
            }
        }
        solution = SolvedManifest.fromdict(
            dict([
                ('version', '1.0.0'),
                (
                    'dependencies',
                    {
                        'foo': {
                            'component_hash': None,
                            'source': {'type': 'local', 'path': release_component_path},
                            'version': '1.0.0',
                        }
                    },
                ),
                (
                    'manifest_hash',
                    'af4c5d3bd0d0f2bb7985b1a1e78c0cf16d2d4115c0adffb3e084cc3d5f63bf09',
                ),
            ])
        )

        monkeypatch.setenv('IDF_VERSION', '5.0.0')
        manifest_dict['dependencies']['foo']['rules'] = [{'if': 'idf_version > 4'}]
        manifest = Manifest.fromdict(manifest_dict, name='test_manifest')
        project_requirements = ProjectRequirements([manifest])
        assert not is_solve_required(project_requirements, solution)
        captured = capsys.readouterr()
        assert 'solving dependencies.' not in captured.out

        monkeypatch.setenv('IDF_VERSION', '3.0.0')
        manifest_dict['dependencies']['foo']['rules'] = [{'if': 'idf_version > 4'}]
        manifest = Manifest.fromdict(manifest_dict, name='test_manifest')
        project_requirements = ProjectRequirements([manifest])
        assert is_solve_required(project_requirements, solution)
        captured = capsys.readouterr()
        assert 'solving dependencies.' in captured.out

    def test_change_manifest_file_targets(self, monkeypatch):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        manifest = Manifest.fromdict({'targets': ['esp32']}, name='test_manifest')
        solution = SolvedManifest.fromdict(
            dict([
                ('version', '1.0.0'),
                (
                    'manifest_hash',
                    '1d0802987b5b8267a89f85398234e02f46a358ff13d321e2bc1eda3049a33ee6',
                ),
            ])
        )
        project_requirements = ProjectRequirements([manifest])
        assert not is_solve_required(project_requirements, solution)  # change it back

        manifest = Manifest.fromdict({'targets': ['esp32']}, name='test_manifest')
        manifest.targets = ['esp32s2', 'esp32s3']
        project_requirements = ProjectRequirements([manifest])
        assert is_solve_required(project_requirements, solution)  # Different idf target

        manifest = Manifest.fromdict({'targets': ['esp32']}, name='test_manifest')
        manifest.targets = ['esp32']
        project_requirements = ProjectRequirements([manifest])
        assert not is_solve_required(project_requirements, solution)  # change it back

    def test_empty_manifest_file(self, monkeypatch):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        solution = SolvedManifest.fromdict(
            dict([
                ('version', '1.0.0'),
                (
                    'manifest_hash',
                    '16d1de584caf3b1e92c92078bbabb5972509c96e44b169ec877d45e4d7716b67',
                ),
            ])
        )

        manifest = Manifest.fromdict({'targets': ['esp32']}, name='test_manifest')
        project_requirements = ProjectRequirements([manifest])
        assert is_solve_required(project_requirements, solution)  # Different idf target

        manifest = Manifest.fromdict({}, name='test_manifest')
        project_requirements = ProjectRequirements([manifest])
        assert not is_solve_required(project_requirements, solution)  # change it back

    def test_empty_lock(self, monkeypatch, capsys):
        solution = SolvedManifest.fromdict(EMPTY_LOCK)

        manifest = Manifest.fromdict({}, name='test_manifest')
        project_requirements = ProjectRequirements([manifest])
        assert is_solve_required(project_requirements, solution)
        captured = capsys.readouterr()

        assert "Dependencies lock doesn't exist, solving dependencies" in captured.out

    def test_update_local_dependency_change_version(self, release_component_path, tmp_path, capsys):
        project_dir = str(tmp_path / 'cmp')
        shutil.copytree(release_component_path, project_dir)

        manifest_dict = {'dependencies': {'cmp': {'path': project_dir}}}
        manifest = Manifest.fromdict(manifest_dict, name='test_manifest')
        project_requirements = ProjectRequirements([manifest])

        components = [
            SolvedComponent(
                name='cmp',
                version=ComponentVersion('1.0.0'),
                source=LocalSource({'path': project_dir}),
                component_hash=None,
            ),
        ]

        solution = SolvedManifest(components, manifest_hash=project_requirements.manifest_hash)

        assert not is_solve_required(project_requirements, solution)

        manifest_manager = ManifestManager(project_dir, 'cmp', check_required_fields=True)
        manifest_manager.manifest_tree['version'] = '1.0.1'
        manifest_manager.dump(str(project_dir))

        assert is_solve_required(project_requirements, solution)
        captured = capsys.readouterr()

        assert 'version has changed from 1.0.0 to 1.0.1, solving dependencies' in captured.out

    def test_update_local_dependency_change_file_not_trigger(
        self, release_component_path, tmp_path, capsys
    ):
        """Check that change in local dependency file doesn't trigger solve"""
        project_dir = str(tmp_path / 'cmp')
        shutil.copytree(release_component_path, project_dir)

        manifest_dict = {'dependencies': {'cmp': {'path': project_dir}}}
        manifest = Manifest.fromdict(manifest_dict, name='test_manifest')
        project_requirements = ProjectRequirements([manifest])

        components = [
            SolvedComponent(
                name='cmp',
                version=ComponentVersion('1.0.0'),
                source=LocalSource({'path': project_dir}),
                component_hash=None,
            ),
        ]

        solution = SolvedManifest(components, manifest_hash=project_requirements.manifest_hash)

        assert not is_solve_required(project_requirements, solution)

        with open(os.path.join(project_dir, 'cmp.c'), 'w') as f:
            f.write('File Changed')

        assert not is_solve_required(project_requirements, solution)
