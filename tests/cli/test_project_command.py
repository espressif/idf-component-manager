# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from idf_component_manager.core import ComponentManager


def test_create_project_from_example_non_default_registry(mocker, invoke_cli):
    mocker.patch('idf_component_manager.core.ComponentManager.create_project_from_example')

    invoke_cli(
        'project',
        'create-from-example',
        'test/cmp=1.0.0:ex',
        '--profile',
        'non-default',
    )
    ComponentManager.create_project_from_example.assert_called_once_with(
        'test/cmp=1.0.0:ex', path=None, profile_name='non-default'
    )


def test_check_deprecated_default_registry(mocker, invoke_cli):
    mocker.patch('idf_component_manager.core.ComponentManager.create_project_from_example')

    invoke_cli(
        'project',
        'create-from-example',
        'test/cmp=1.0.0:ex',
        '--profile',
        'non-default',
    )
    ComponentManager.create_project_from_example.assert_called_once_with(
        'test/cmp=1.0.0:ex', path=None, profile_name='non-default'
    )
