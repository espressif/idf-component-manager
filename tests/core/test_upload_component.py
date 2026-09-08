# SPDX-FileCopyrightText: 2024-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import shutil
from pathlib import Path

import pytest
import requests_mock

from idf_component_manager.core import ComponentManager
from idf_component_tools.archive_tools import unpack_archive
from idf_component_tools.errors import FatalError, NothingToDoError
from tests.network_test_utils import use_vcr_or_real_env

# ruff: noqa: ARG001


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_upload_component.yaml')
@pytest.mark.network
def test_upload_component(mock_registry, mock_upload, pre_release_component_path, component_name):
    manager = ComponentManager(path=pre_release_component_path)
    name_to_upload = f'{component_name}_upload'

    manager.upload_component(name_to_upload, namespace='test_component_manager')


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_upload_component_with_example_readme.yaml')
@pytest.mark.network
def test_upload_component_with_example_readme(
    mock_registry, mock_upload, cmp_with_example, component_name, tmp_path
):
    component_path = tmp_path / 'cmp'
    shutil.copytree(cmp_with_example, str(component_path), ignore=shutil.ignore_patterns('dist'))
    (component_path / 'examples' / 'cmp_ex' / 'README.md').write_text(
        '# Example readme\n\nDescription of the example.\n'
    )

    manager = ComponentManager(path=str(component_path))
    name_to_upload = f'{component_name}_example_readme'

    manager.upload_component(name_to_upload, namespace='test_component_manager')

    # The readme of the example is a part of the uploaded archive
    (archive_path,) = Path(manager.default_dist_path).glob(f'{name_to_upload}_*.tgz')
    unpack_archive(str(archive_path), str(tmp_path / 'unpack'))
    assert (
        'Description of the example.'
        in (tmp_path / 'unpack' / 'examples' / 'cmp_ex' / 'README.md').read_text()
    )


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
