# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
def test_upload_component_with_invalid_name(invoke_cli):
    result = invoke_cli(
        'component',
        'upload',
        '--name',
        'тест',
    )

    assert result.exit_code == 2
    assert 'Invalid value for' in result.output
