# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
from pathlib import Path

import pytest

from idf_component_manager.core import ComponentManager
from idf_component_tools.errors import FatalError
from idf_component_tools.registry.api_client import APIClient
from idf_component_tools.registry.client_errors import ComponentNotFound
from tests.network_test_utils import use_vcr_or_real_env


def setup_yankable_component(component_name, fixtures_path):
    api_client = APIClient(
        registry_url=os.environ.get('IDF_COMPONENT_REGISTRY_URL'),
        api_token=os.environ.get('IDF_COMPONENT_API_TOKEN'),
        default_namespace='test_component_manager',
    )
    test_path = Path(fixtures_path) / 'components' / 'cmp_with_example'
    manager = ComponentManager(path=test_path)
    try:
        v = api_client.versions(f'test_component_manager/{component_name}', spec='1.0.0')
        if not v.versions:
            manager.upload_component(component_name, '1.0.0', namespace='test_component_manager')
    except ComponentNotFound:
        manager.upload_component(component_name, '1.0.0', namespace='test_component_manager')


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_yank_version_success.yaml')
@pytest.mark.network
def test_yank_component_version(mock_registry, mock_yank, tmp_path, component_name, fixtures_path):
    manager = ComponentManager(path=str(tmp_path))

    component_name = f'{component_name}_yankable'
    setup_yankable_component(component_name, fixtures_path)

    manager.yank_version(
        component_name, '1.0.0', 'critical test', namespace='test_component_manager'
    )


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_yank_version_not_found.yaml')
@pytest.mark.network
def test_yank_component_version_not_exists(mock_registry, tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    with pytest.raises(
        FatalError,
        match='Version 1.2.0 of the component "test_component_manager/cmp" is not on the registry',
    ):
        manager.yank_version('cmp', '1.2.0', 'critical test', namespace='test_component_manager')
