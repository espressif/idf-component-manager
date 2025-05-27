# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import filecmp
import logging
import os
import shutil
import textwrap
import time
from io import open
from pathlib import Path

import pytest
import requests
import requests_mock
from ruamel.yaml import YAML

from idf_component_manager.dependencies import is_solve_required
from idf_component_tools import LOGGING_NAMESPACE, setup_logging
from idf_component_tools.build_system_tools import get_idf_version
from idf_component_tools.errors import LockError
from idf_component_tools.lock import EMPTY_LOCK, LockFile, LockManager
from idf_component_tools.manager import ManifestManager
from idf_component_tools.manifest import (
    ComponentRequirement,
    Manifest,
    SolvedComponent,
    SolvedManifest,
)
from idf_component_tools.sources import IDFSource, LocalSource, WebServiceSource
from idf_component_tools.utils import ComponentVersion, ProjectRequirements


@pytest.fixture
def valid_lock_path(fixtures_path):
    return os.path.join(
        fixtures_path,
        'locks',
        'dependencies.lock',
    )


@pytest.fixture
def valid_solution_dependency_dict(fixtures_path):
    with open(os.path.join(fixtures_path, 'locks', 'dependencies.lock')) as f:
        d = YAML(typ='safe').load(f)

    return d['dependencies']


@pytest.fixture
def valid_solution_hash(fixtures_path):
    with open(os.path.join(fixtures_path, 'locks', 'dependencies.lock')) as f:
        d = YAML(typ='safe').load(f)

    return d['manifest_hash']


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


class TestLockManager(object):
    def test_load_valid_lock(self, valid_lock_path):
        parser = LockManager(valid_lock_path)

        lock = parser.load()
        assert parser.exists()

        test_cmp = [cmp for cmp in lock.dependencies if cmp.name == 'espressif/test_cmp'][0]
        assert test_cmp.source.registry_url == 'https://repo.example.com'

    def test_lock_dump_with_solution(self, tmp_path, monkeypatch, manifest_path, valid_lock_path):
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '4.4.4')
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')

        lock = LockManager(lock_path)
        manifest = ManifestManager(manifest_path, name='test').load()
        components = [
            SolvedComponent(
                name='idf',
                version=ComponentVersion('4.4.4'),
                source=IDFSource(),
            ),
            SolvedComponent(
                name='espressif/test_cmp',
                version=ComponentVersion('1.2.7'),
                source=WebServiceSource(registry_url='https://repo.example.com'),
                # pragma: allowlist nextline secret
                component_hash='f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b',
            ),
        ]

        solution = SolvedManifest(dependencies=components, manifest_hash=manifest.manifest_hash)
        lock.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    def test_lock_dump_with_current_solution(self, tmp_path, monkeypatch, manifest_path, caplog):
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '4.4.4')
        monkeypatch.setenv('IDF_TARGET', 'esp32')

        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')

        lock = LockManager(lock_path)
        manifest = ManifestManager(manifest_path, name='test').load()
        project_requirements = ProjectRequirements([manifest])

        components = [
            SolvedComponent(
                name='idf',
                version=ComponentVersion('4.4.4'),
                source=IDFSource(),
            ),
            SolvedComponent(
                name='espressif/test_cmp',
                version=ComponentVersion('1.2.7'),
                source=WebServiceSource(registry_url='https://repo.example.com'),
                # pragma: allowlist nextline secret
                component_hash='f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b',
                targets=['esp32', 'esp32s2'],
                dependencies=[
                    ComponentRequirement(
                        name='idf',
                        version='<5.1',
                        source=IDFSource(),
                    )
                ],
            ),
        ]

        solution = SolvedManifest(
            dependencies=components,
            manifest_hash=project_requirements.manifest_hash,
            target='esp32',
            direct_dependencies=[
                'espressif/some_component',
                'espressif/test',
                'espressif/test-1',
                'idf',
            ],  # this is not reflecting the actual dependencies, but to fool the solver.
            # the direct_dependencies is calculated by the fixtures/idf_component.yml
        )
        assert lock.dump(solution)
        touch_timestamp = os.path.getmtime(lock_path)

        # solution with a different manifest hash
        solution.manifest_hash = 'x' * 64
        assert is_solve_required(ProjectRequirements([manifest]), solution)
        time.sleep(0.01)  # in case the filesystem has a low resolution timestamp
        assert lock.dump(solution)
        assert os.path.getmtime(lock_path) > touch_timestamp

        # reset solution manifest hash
        solution.manifest_hash = project_requirements.manifest_hash

        # idf change to 5.0, shouldn't trigger solve, but update the lock
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.0.0')
        assert not is_solve_required(ProjectRequirements([manifest]), solution)
        assert lock.dump(solution)

        # idf change to 5.1, should trigger solve, since dependency idf<5.1
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.1.0')
        caplog.clear()
        with caplog.at_level(logging.INFO, logger=LOGGING_NAMESPACE):
            assert is_solve_required(ProjectRequirements([manifest]), solution)
            # 3 are the retry /api calls, 1 is the actual solve
            assert len(caplog.records) == 1
            assert (
                'espressif/test_cmp (1.2.7) is not compatible with the current idf version'
                in caplog.records[0].message
            )

        # reset idf version
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '4.4.4')

        # target change to esp32s2, shouldn't trigger solve, but update the lock
        monkeypatch.setenv('IDF_TARGET', 'esp32s2')
        assert not is_solve_required(ProjectRequirements([manifest]), solution)
        assert lock.dump(solution)

        # target change to esp32s3, should trigger solve, since dependency target esp32, esp32s2
        monkeypatch.setenv('IDF_TARGET', 'esp32s3')
        caplog.clear()
        with caplog.at_level(logging.INFO, logger=LOGGING_NAMESPACE):
            assert is_solve_required(ProjectRequirements([manifest]), solution)
            # 3 are the retry /api calls, 1 is the actual solve
            assert len(caplog.records) == 1
            assert (
                'espressif/test_cmp (1.2.7) is not compatible with the current target esp32s3'
                in caplog.records[0].message
            )

    def test_lock_dump_with_dictionary(
        self,
        tmp_path,
        monkeypatch,
        valid_lock_path,
        valid_solution_dependency_dict,
        valid_solution_hash,
    ):
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '4.4.4')
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        parser = LockManager(lock_path)
        solution = LockFile.fromdict(
            dict([
                ('version', '2.0.0'),
                ('dependencies', valid_solution_dependency_dict),
                ('manifest_hash', valid_solution_hash),
            ])
        )

        parser.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)

    def test_lock_dump(
        self,
        tmp_path,
        monkeypatch,
        valid_lock_path,
        valid_solution_dependency_dict,
        valid_solution_hash,
    ):
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '4.4.4')
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')

        parser = LockManager(lock_path)
        solution = parser.load()
        solution.manifest_hash = valid_solution_hash

        for name, details in valid_solution_dependency_dict.items():
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

    def test_minimal_lock(self, tmp_path, monkeypatch, valid_solution_hash):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.1.0')
        lock_path = os.path.join(str(tmp_path), 'dependencies.lock')
        parser = LockManager(lock_path)
        solution = SolvedManifest.fromdict({
            'manifest_hash': valid_solution_hash,
            'dependencies': {
                'idf': {
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
                source:
                  type: idf
                version: 5.1.0
            manifest_hash: {}
            target: esp32
            version: 2.0.0
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

    def test_no_internet_connection(self, caplog):
        manifest = Manifest.fromdict({
            'dependencies': {
                'idf': '4.4.0',
                'example/cmp': '*',
            }
        })
        project_requirements = ProjectRequirements([manifest])
        solution = SolvedManifest.fromdict({
            'direct_dependencies': ['example/cmp', 'idf'],
            'dependencies': {
                'example/cmp': {
                    # pragma: allowlist nextline secret
                    'component_hash': '8644358a11a35a986b0ce4d325ba3d1aa9491b9518111acd4ea9447f11dc47c1',
                    'source': {
                        'service_url': 'https://ohnoIdonthaveinternetconnection.com',
                        'type': 'service',
                    },
                    'version': '3.3.7',
                },
                'idf': {
                    'source': {
                        'type': 'idf',
                    },
                    'version': '4.4.0',
                },
            },
            'manifest_hash': project_requirements.manifest_hash,
        })

        caplog.set_level(logging.INFO, logger=LOGGING_NAMESPACE)
        assert not is_solve_required(project_requirements, solution)
        assert any(
            'Cannot establish a connection to the component registry. '
            'Skipping checks of dependency changes.' in record.message
            for record in caplog.records
        )

    def test_change_manifest_file_idf_version_required_in_dependencies_rules(
        self, monkeypatch, capsys, release_component_path
    ):
        setup_logging()  # test the output of why the solver is required
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '4.4.0')
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
        manifest = Manifest.fromdict(manifest_dict)
        project_requirements = ProjectRequirements([manifest])
        solution = SolvedManifest.fromdict({
            'direct_dependencies': ['espressif/foo'],
            'dependencies': {
                'espressif/foo': {
                    'source': {'type': 'local', 'path': release_component_path},
                    'version': '1.0.0',
                }
            },
            'manifest_hash': project_requirements.manifest_hash,
        })

        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.0.0')
        manifest = Manifest.fromdict(manifest_dict)
        project_requirements = ProjectRequirements([manifest])
        assert not is_solve_required(project_requirements, solution)
        captured = capsys.readouterr()
        assert 'solving dependencies.' not in captured.out

        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '3.0.0')
        manifest = Manifest.fromdict(manifest_dict)
        project_requirements = ProjectRequirements([manifest])
        assert is_solve_required(project_requirements, solution)
        captured = capsys.readouterr()
        assert 'Direct dependencies have changed, solving dependencies' in captured.out

    def test_change_manifest_file_targets(self, monkeypatch):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        manifest = Manifest.fromdict({'targets': ['esp32']})
        project_requirements = ProjectRequirements([manifest])
        solution = SolvedManifest.fromdict({
            'manifest_hash': project_requirements.manifest_hash,
        })
        assert not is_solve_required(project_requirements, solution)

        manifest = Manifest.fromdict({'targets': ['esp32']})
        manifest.targets = ['esp32s2', 'esp32s3']
        project_requirements = ProjectRequirements([manifest])
        assert is_solve_required(project_requirements, solution)  # Different idf target

        manifest = Manifest.fromdict({'targets': ['esp32']})
        manifest.targets = ['esp32']
        project_requirements = ProjectRequirements([manifest])
        assert not is_solve_required(project_requirements, solution)  # change it back

    def test_empty_manifest_file(self, monkeypatch):
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        manifest = Manifest.fromdict({})
        project_requirements = ProjectRequirements([manifest])
        solution = SolvedManifest.fromdict({
            'manifest_hash': project_requirements.manifest_hash,
        })

        manifest = Manifest.fromdict({'targets': ['esp32']})
        project_requirements = ProjectRequirements([manifest])
        assert is_solve_required(project_requirements, solution)  # Different idf target

        manifest = Manifest.fromdict({})
        project_requirements = ProjectRequirements([manifest])
        assert not is_solve_required(project_requirements, solution)  # change it back

    def test_empty_lock(self, caplog):
        solution = SolvedManifest.fromdict(EMPTY_LOCK)

        manifest = Manifest.fromdict({})
        project_requirements = ProjectRequirements([manifest])
        with caplog.at_level(logging.INFO, logger=LOGGING_NAMESPACE):
            assert is_solve_required(project_requirements, solution)
            assert len(caplog.records) == 1
            assert (
                "Dependencies lock doesn't exist, solving dependencies" in caplog.records[0].message
            )

    def test_update_local_dependency_change_version(self, release_component_path, tmp_path, caplog):
        project_dir = str(tmp_path / 'cmp')
        shutil.copytree(release_component_path, project_dir)

        manifest = Manifest.fromdict({'dependencies': {'cmp': {'path': project_dir}}})
        project_requirements = ProjectRequirements([manifest])

        solution = SolvedManifest(
            direct_dependencies=['cmp'],
            dependencies=[
                SolvedComponent(
                    name='cmp',
                    version=ComponentVersion('1.0.0'),
                    source=LocalSource(path=project_dir),
                ),
            ],
            manifest_hash=project_requirements.manifest_hash,
        )

        assert not is_solve_required(project_requirements, solution)

        manifest_manager = ManifestManager(project_dir, 'cmp')
        manifest_manager.manifest.version = '1.0.1'
        manifest_manager.dump(str(project_dir))

        with caplog.at_level(logging.INFO, logger=LOGGING_NAMESPACE):
            assert is_solve_required(project_requirements, solution)
            assert len(caplog.records) == 1
            assert (
                'version has changed from 1.0.0 to 1.0.1, solving dependencies'
                in caplog.records[0].message
            )

    def test_update_local_dependency_change_file_not_trigger(
        self, release_component_path, tmp_path
    ):
        """Check that change in local dependency file doesn't trigger solve"""
        project_dir = str(tmp_path / 'cmp')
        shutil.copytree(release_component_path, project_dir)

        manifest_dict = {'dependencies': {'cmp': {'path': project_dir}}}
        manifest = Manifest.fromdict(manifest_dict)
        project_requirements = ProjectRequirements([manifest])

        components = [
            SolvedComponent(
                name='cmp',
                version=ComponentVersion('1.0.0'),
                source=LocalSource(path=project_dir),
                component_hash=None,
            ),
        ]

        solution = SolvedManifest(
            direct_dependencies=['cmp'],
            dependencies=components,
            manifest_hash=project_requirements.manifest_hash,
        )

        assert not is_solve_required(project_requirements, solution)

        with open(os.path.join(project_dir, 'cmp.c'), 'w') as f:
            f.write('File Changed')

        assert not is_solve_required(project_requirements, solution)
