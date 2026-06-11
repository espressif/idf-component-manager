# SPDX-FileCopyrightText: 2024-2026 Espressif Systems (Shanghai) CO LTD
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


def test_upload_component_version_and_archive_not_mutually_exclusive(mocker):
    """--version and --archive can be supplied together.

    Both options are accepted at parse time and forwarded to
    ``upload_component``; the archive callback requires the file to exist and
    have a recognised extension, so we create a real ``.tgz`` file.
    """
    mock_upload = mocker.patch('idf_component_manager.core.ComponentManager.upload_component')
    from click.testing import CliRunner

    from idf_component_manager.cli.core import initialize_cli

    runner = CliRunner()
    with runner.isolated_filesystem():
        # validate_if_archive checks existence + extension; satisfy both.
        import tarfile

        with tarfile.open('cmp.tgz', 'w:gz'):
            pass

        result = runner.invoke(
            initialize_cli(),
            [
                'component',
                'upload',
                '--name',
                'cmp',
                '--version',
                '1.0.0',
                '--archive',
                'cmp.tgz',
            ],
        )

    assert result.exit_code == 0, result.output
    assert 'mutually exclusive' not in result.output
    mock_upload.assert_called_once()
    _args, kwargs = mock_upload.call_args
    assert kwargs.get('version') == '1.0.0'
    assert kwargs.get('archive') is not None and str(kwargs['archive']).endswith('cmp.tgz')
