# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_manager.__main__ import main


def test_cli(mocker):
    """Test that safe_cli is executed"""
    mock_initialize_cli = mocker.patch('idf_component_manager.cli.core.initialize_cli')

    main()

    mock_initialize_cli.assert_called_once_with()
