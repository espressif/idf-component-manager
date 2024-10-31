# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_manager.__main__ import main


def test_cli(mocker):
    """Test that safe_cli is executed"""
    mock_initialize_cli = mocker.patch('idf_component_manager.cli.core.initialize_cli')

    main()

    mock_initialize_cli.assert_called_once_with()


def test_raise_exception_on_warnings(invoke_cli):
    output = invoke_cli(
        '--warnings-as-errors', 'project', 'create-from-example', 'example/cmp=3.3.8:cmp'
    )

    assert output.exit_code == 1
    assert (
        'The version "3.3.8" of the "example/cmp" component you have selected has been '
        'yanked from the repository' in str(output.exception)
    )
