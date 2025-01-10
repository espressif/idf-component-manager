# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

import pytest

from idf_component_manager.dependencies import download_project_dependencies
from idf_component_tools.debugger import DEBUG_INFO_COLLECTOR
from idf_component_tools.errors import SolverError
from idf_component_tools.manifest import Manifest
from idf_component_tools.utils import ProjectRequirements
from tests.network_test_utils import use_vcr_or_real_env


@pytest.fixture
def reset_debug_info_collector():
    collector = DEBUG_INFO_COLLECTOR.get()
    collector.msgs.clear()
    collector.dep_introduced_by.clear()
    yield


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_webservice_target.yaml')
@pytest.mark.network
def test_target_exists(tmp_path, monkeypatch, mock_registry, reset_debug_info_collector):  # noqa: ARG001
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.3.0')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))
    monkeypatch.setenv('IDF_TARGET', 'esp32s2')

    registry_url = os.getenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:5000')
    manifest = Manifest.fromdict({
        'dependencies': {
            'test_component_manager/pre': {'version': '*', 'registry_url': f'{registry_url}'}
        }
    })

    with pytest.raises(SolverError):
        download_project_dependencies(
            ProjectRequirements(manifests=[manifest]),
            lock_path=tmp_path / 'test.lock',
            managed_components_path='managed_components',
        )
    messages = DEBUG_INFO_COLLECTOR.get().msgs
    assert len(messages) == 1
    assert (
        'Component "test_component_manager/pre" (requires in ) has suitable versions for other targets:'
    ) in messages[0]
    assert 'esp32' in messages[0]
    assert 'Is your current target esp32s2 set correctly?' in messages[0]


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_webservice_pre_release.yaml')
@pytest.mark.network
def test_pre_release_exists(tmp_path, monkeypatch, mock_registry, reset_debug_info_collector):  # noqa: ARG001
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
        download_project_dependencies(
            ProjectRequirements(manifests=[manifest]),
            lock_path=tmp_path / 'test.lock',
            managed_components_path='managed_components',
        )
    messages = DEBUG_INFO_COLLECTOR.get().msgs
    assert len(messages) == 1
    assert (
        'Component "test_component_manager/pre" (requires in ) has some pre-release versions: "0.0.5-alpha1" '
        'satisfies your requirements. '
        'To allow pre-release versions add "pre_release: true" '
        'to the dependency in the manifest.'
    ) in messages[0]
