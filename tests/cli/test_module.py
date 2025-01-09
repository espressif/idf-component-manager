# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


from idf_component_manager.__main__ import main
from tests.network_test_utils import use_vcr_or_real_env


def test_cli(mocker):
    """Test that safe_cli is executed"""
    mock_initialize_cli = mocker.patch('idf_component_manager.cli.core.initialize_cli')

    main()

    mock_initialize_cli.assert_called_once_with()


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_exception_on_warnings.yaml')
def test_raise_exception_on_warnings(invoke_cli, mock_registry):
    output = invoke_cli(
        '--warnings-as-errors',
        'project',
        'create-from-example',
        'test_component_manager/ynk=1.0.0:cmp_ex',
    )

    assert output.exit_code == 1
    assert (
        'The following versions of the "test_component_manager/ynk" component have been yanked:\n'
        in str(output.exception)
    )
