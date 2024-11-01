# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import shutil

import pytest
import requests_mock
import vcr

from idf_component_manager.core import ComponentManager
from idf_component_tools import LOGGING_NAMESPACE
from idf_component_tools.errors import FatalError, NothingToDoError

# ruff: noqa: ARG001


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_upload_component.yaml')
def test_upload_component(mock_registry, pre_release_component_path, caplog):
    manager = ComponentManager(path=pre_release_component_path)

    with caplog.at_level(logging.WARNING, logger=LOGGING_NAMESPACE):
        manager.upload_component('cmp')
        assert len(caplog.records) == 2
        assert 'A component description has not been provided in the manifest file.' in caplog.text
        assert 'A homepage URL has not been provided in the manifest file.' in caplog.text


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


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_check_only_component.yaml')
def test_check_only_upload_component(mock_registry, pre_release_component_path):
    manager = ComponentManager(path=pre_release_component_path)

    manager.upload_component(
        'cmp',
        check_only=True,
    )


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_allow_existing_component.yaml')
def test_allow_existing_component(mock_registry, release_component_path, tmp_path):
    shutil.copytree(release_component_path, str(tmp_path / 'cmp'))
    manager = ComponentManager(path=str(tmp_path / 'cmp'))

    manager.upload_component(
        'cmp',
        allow_existing=True,
    )


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_validate_component.yaml')
def test_validate_component(mock_registry_without_token, pre_release_component_path):
    manager = ComponentManager(path=pre_release_component_path)

    manager.upload_component(
        'cmp',
        dry_run=True,
    )


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_upload_component_skip_pre.yaml')
def test_upload_component_skip_pre(mock_registry, pre_release_component_path):
    manager = ComponentManager(path=pre_release_component_path)

    with pytest.raises(NothingToDoError) as e:
        manager.upload_component(
            'cmp',
            skip_pre_release=True,
        )

        assert str(e.value).startswith('Skipping pre-release')
