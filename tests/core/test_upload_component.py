# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import shutil

import pytest
import requests_mock

from idf_component_manager.core import ComponentManager
from idf_component_tools.errors import FatalError, NothingToDoError
from tests.network_test_utils import use_vcr_or_real_env

# ruff: noqa: ARG001


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_upload_component.yaml')
@pytest.mark.network
def test_upload_component(mock_registry, mock_upload, pre_release_component_path, component_name):
    manager = ComponentManager(path=pre_release_component_path)
    name_to_upload = f'{component_name}_upload'

    manager.upload_component(name_to_upload, namespace='test_component_manager')


def test_upload_component_http_error(mock_registry, pre_release_component_path):
    with requests_mock.Mocker() as m:
        # Mock the HTTP request to return a 502 error
        m.get(
            'http://localhost:5000/api/components/espressif/cmp',
            status_code=502,
            json={'error': 'Err', 'messages': ['Some error messages']},
        )

        with pytest.raises(
            FatalError,
            match='Internal server error happened while processing request.\n'
            'URL: http://localhost:5000/api/components/espressif/cmp\n'
            'Status code: 502 Bad Gateway',
        ):
            manager = ComponentManager(path=pre_release_component_path)
            manager.upload_component('cmp')


def test_check_only_upload_component(pre_release_component_path):
    manager = ComponentManager(path=pre_release_component_path)

    manager.upload_component(
        'cmp',
        check_only=True,
    )


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_allow_existing_component.yaml')
@pytest.mark.network
def test_allow_existing_component(mock_registry, mock_upload, release_component_path, tmp_path):
    shutil.copytree(release_component_path, str(tmp_path / 'cmp'))
    manager = ComponentManager(path=str(tmp_path / 'cmp'))

    manager.upload_component(
        'cmp',
        allow_existing=True,
        namespace='test_component_manager',
    )


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_validate_component.yaml')
@pytest.mark.network
def test_validate_component(mock_registry_without_token, mock_upload, pre_release_component_path):
    manager = ComponentManager(path=pre_release_component_path)

    manager.upload_component(
        'cmp',
        dry_run=True,
        namespace='test_component_manager',
    )


def test_upload_component_skip_pre(pre_release_component_path):
    manager = ComponentManager(path=pre_release_component_path)

    with pytest.raises(NothingToDoError) as e:
        manager.upload_component(
            'cmp',
            skip_pre_release=True,
            namespace='test_component_manager',
        )

        assert str(e.value).startswith('Skipping pre-release')
