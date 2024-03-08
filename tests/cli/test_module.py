# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import vcr

from idf_component_manager.__main__ import main
from idf_component_manager.core import ComponentManager, get_processing_timeout


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_upload_component.yaml')
def test_upload_component(mock_registry, pre_release_component_path):
    main(['upload-component', '--path', pre_release_component_path, '--name', 'cmp'])


def test_upload_component_status(mocker):
    mocker.patch('idf_component_manager.core.ComponentManager.upload_component_status')
    main(['upload-component-status', '--job', 'some_id'])
    ComponentManager.upload_component_status.assert_called_once_with(
        job_id='some_id', service_profile='default'
    )


def test_pack_component(mocker):
    mocker.patch('idf_component_manager.core.ComponentManager.pack_component')
    main(['pack-component', '--name', 'cmp', '--version', '1.0.0'])
    ComponentManager.pack_component.assert_called_once_with(name='cmp', version='1.0.0')


def test_create_project_from_example(mocker):
    mocker.patch('idf_component_manager.core.ComponentManager.create_project_from_example')
    main([
        'create-project-from-example',
        '--name',
        'cmp',
        '--namespace',
        'test',
        '--version',
        '1.0.0',
        '--example',
        'ex',
    ])
    ComponentManager.create_project_from_example.assert_called_once_with(
        example='test/cmp=1.0.0:ex'
    )


def test_delete_version(mocker):
    mocker.patch('idf_component_manager.core.ComponentManager.delete_version')
    main([
        'delete-version',
        '--name',
        'cmp',
        '--version',
        '1.0.0',
        '--namespace',
        'test',
    ])
    ComponentManager.delete_version.assert_called_once_with(
        name='cmp', version='1.0.0', service_profile='default', namespace='test'
    )


def test_env_job_timeout_empty(monkeypatch):
    monkeypatch.setenv('COMPONENT_MANAGER_JOB_TIMEOUT', 300)
    assert get_processing_timeout() == 300
