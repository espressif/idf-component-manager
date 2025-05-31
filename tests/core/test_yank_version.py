# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

import pytest

from idf_component_manager.core import ComponentManager
from idf_component_tools.errors import FatalError
from idf_component_tools.registry.api_client import APIClient
from idf_component_tools.registry.client_errors import ComponentNotFound
from tests.network_test_utils import use_vcr_or_real_env


def setup_yankable_component(component_name, cmp_with_example):
    api_client = APIClient(
        registry_url=os.environ.get('IDF_COMPONENT_REGISTRY_URL'),
        api_token=os.environ.get('IDF_COMPONENT_API_TOKEN'),
        default_namespace='test_component_manager',
    )
    manager = ComponentManager(path=cmp_with_example)
    try:
        v = api_client.versions(f'test_component_manager/{component_name}', spec='1.0.0')
        if not v.versions:
            manager.upload_component(component_name, '1.0.0', namespace='test_component_manager')
    except ComponentNotFound:
        manager.upload_component(component_name, '1.0.0', namespace='test_component_manager')


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_yank_version_success.yaml')
@pytest.mark.network
def test_yank_component_version(
    mock_registry,  # noqa: ARG001
    mock_yank,  # noqa: ARG001
    tmp_path,
    component_name,
    cmp_with_example,
):
    manager = ComponentManager(path=str(tmp_path))

    component_name = f'{component_name}_yankable'
    setup_yankable_component(component_name, cmp_with_example)

    manager.yank_version(
        component_name, '1.0.0', 'critical test', namespace='test_component_manager'
    )


@pytest.mark.network
def test_yank_component_version_not_exists(mock_yank_404, tmp_path):  # noqa: ARG001
    manager = ComponentManager(path=str(tmp_path))
    with pytest.raises(
        FatalError, match='Version "1.2.0" of component "cmp" was not found in the registry.'
    ):
        manager.yank_version('cmp', '1.2.0', 'critical test', namespace='test_component_manager')
