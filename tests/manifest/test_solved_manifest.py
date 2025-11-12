# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os

from idf_component_tools.lock import LockManager
from idf_component_tools.manager import ManifestManager
from idf_component_tools.manifest import SolvedComponent
from idf_component_tools.sources import WebServiceSource


class TestSolverResult:
    def test_load_valid_lock(self, fixtures_path):
        valid_lock_path = os.path.join(
            fixtures_path,
            'locks',
            'dependencies.lock',
        )

        manager = LockManager(valid_lock_path)
        solution = manager.load()

        assert manager.exists()
        assert len(solution.dependencies) == 2
        cmp = solution.dependencies[0]
        assert isinstance(cmp, SolvedComponent)
        assert isinstance(cmp.source, WebServiceSource)
        assert cmp.source.registry_url == 'https://repo.example.com'
        assert str(solution.dependencies[1].version) == '4.4.4'

    def test_solve_optional_dependency(self, monkeypatch, release_component_path):
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.0.0')
        monkeypatch.setenv('IDF_TARGET', 'esp32')

        manifest_manager = ManifestManager(release_component_path, 'test')
        manifest_manager.manifest.dependencies = {
            'espressif/test': '1.2.3',
            'pest': {'version': '3.2.1'},
            'foo': {
                'version': '1.0.0',
                'rules': [
                    {'if': 'idf_version == 5.0.0'},
                    {'if': 'target not in [esp32, esp32c3]'},
                ],
            },
        }
        manifest = manifest_manager.load()
        assert len(manifest.requirements) == 2

        # name is the field from the manifest, don't touch it
        assert manifest.requirements[0].name == 'espressif/pest'
        assert manifest.requirements[1].name == 'espressif/test'

    def test_solve_mixed_case_web_dependency(self, release_component_path):
        manifest_manager = ManifestManager(release_component_path, 'test')
        manifest_manager.manifest.dependencies = {
            'EsPrEsSiF/DeP_CmP': {'version': '3.2.1', 'registry_url': 'https://repo.example.com'},
        }
        manifest_with_mixed_case = manifest_manager.load()

        assert manifest_with_mixed_case.requirements[0].name == 'espressif/dep_cmp'
