# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import os

import pytest

from idf_component_manager.dependencies import download_project_dependencies
from idf_component_tools import LOGGING_NAMESPACE
from idf_component_tools.errors import SolverError
from idf_component_tools.manifest import Manifest
from idf_component_tools.utils import ProjectRequirements
from tests.network_test_utils import use_vcr_or_real_env


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_webservice_target.yaml')
@pytest.mark.network
def test_target_exists(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.3.0')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))
    monkeypatch.setenv('IDF_TARGET', 'esp32s2')

    manifest = Manifest.fromdict({
        'dependencies': {
            'test_component_manager/pre': {'version': '*', 'registry_url': 'http://localhost:5000/'}
        }
    })

    with pytest.raises(SolverError):
        with caplog.at_level(logging.WARNING, logger=LOGGING_NAMESPACE):
            download_project_dependencies(
                ProjectRequirements(manifests=[manifest]),
                lock_path=tmp_path / 'test.lock',
                managed_components_path='managed_components',
            )
            assert len(caplog.records) == 1
            assert (
                'Component "example/cmp" has suitable versions for other targets: "esp32". '
                'Is your current target "esp32s2" set correctly?'
            ) in caplog.records[0].message


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_webservice_pre_release.yaml')
@pytest.mark.network
def test_pre_release_exists(tmp_path, monkeypatch, caplog, mock_registry):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.3.0')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))
    monkeypatch.setenv('IDF_TARGET', 'esp32')

    registry_url = os.getenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:5000')
    manifest = Manifest.fromdict({
        'dependencies': {
            'test_component_manager/pre': {'version': '*', 'registry_url': f'{registry_url}'}
        }
    })

    with pytest.raises(SolverError):
        with caplog.at_level(logging.WARNING, logger=LOGGING_NAMESPACE):
            download_project_dependencies(
                ProjectRequirements(manifests=[manifest]),
                lock_path=tmp_path / 'test.lock',
                managed_components_path='managed_components',
            )
            assert len(caplog.records) == 1
            assert (
                'Component "example/cmp" has some pre-release versions: "0.0.5-alpha1" '
                'satisfies your requirements. '
                'To allow pre-release versions add "pre_release: true" '
                'to the dependency in the manifest.'
            ) in caplog.records[0].message
