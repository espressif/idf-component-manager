# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import sys

import requests_mock

from idf_component_tools.config import Config, ConfigManager


def test_login_to_registry(tmp_path, mock_registry, mock_token_information, invoke_cli):  # noqa: ARG001
    output = invoke_cli(
        'registry',
        'login',
        '--no-browser',
        input='test_token',
        env={
            #  non-existing path is to check PACMAN-961
            'IDF_TOOLS_PATH': str(tmp_path / 'non-existing-path')
        },
    )

    assert output.exit_code == 0
    # assert that login url is printed
    assert 'http://localhost:5000/settings/tokens?' in output.output
    assert 'Successfully logged in' in output.output


def test_login_with_non_existing_service_profile(
    monkeypatch,
    tmp_path,
    mock_registry,  # noqa: ARG001
    mock_token_information,  # noqa: ARG001
    invoke_cli,
):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    output = invoke_cli(
        'registry',
        'login',
        '--no-browser',
        '--profile',
        'non-existing',
        input='test_token',
        env={'IDF_TOOLS_PATH': str(tmp_path)},
    )

    config_content = open(str(tmp_path / 'idf_component_manager.yml')).read()

    assert output.exit_code == 0
    # assert that profile is created with a token
    assert 'non-existing' in config_content


def test_login_deprecated_arguments(monkeypatch, tmp_path, mock_token_information, invoke_cli):  # noqa: ARG001
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    output = invoke_cli(
        'registry',
        'login',
        '--no-browser',
        '--registry_url',
        'http://localhost:5000',
        '--default_namespace',
        'testspace',
        input='test_token',
        env={'IDF_TOOLS_PATH': str(tmp_path)},
    )

    config_content = open(str(tmp_path / 'idf_component_manager.yml')).read()

    assert output.exit_code == 0
    # assert that profile is created with provided namespace and registry_url
    assert 'testspace' in config_content
    assert 'http://localhost:5000' in config_content


def test_login_updated_arguments(monkeypatch, tmp_path, mock_token_information, invoke_cli):  # noqa: ARG001
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    output = invoke_cli(
        'registry',
        'login',
        '--no-browser',
        '--registry-url',
        'http://localhost:5000',
        '--default-namespace',
        'testspace',
        input='test_token',
        env={'IDF_TOOLS_PATH': str(tmp_path)},
    )

    config_content = open(str(tmp_path / 'idf_component_manager.yml')).read()

    assert output.exit_code == 0
    # assert that profile is created with provided namespace and registry_url
    assert 'testspace' in config_content
    assert 'http://localhost:5000' in config_content


def test_logout_from_registry(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))
    config = Config.fromdict({
        'profiles': {
            'default': {
                'api_token': 'asdf',
                'registry_url': 'http:/localhost:5000',
            },
        }
    })
    ConfigManager().dump(config)

    with requests_mock.Mocker() as m:
        m.delete(
            'http://localhost:5000/api/tokens/current',
            status_code=204,
        )

        output = invoke_cli('registry', 'logout', env={'IDF_TOOLS_PATH': str(tmp_path)})

        assert m.call_count == 1
        assert m.request_history[0].method == 'DELETE'
        assert m.request_history[0].url == 'http://localhost:5000/api/tokens/current'

    assert 'Successfully logged out' in output.stdout


def test_logout_from_registry_revoked_token(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))
    config = Config.fromdict({
        'profiles': {
            'default': {
                'api_token': 'asdf',
                'registry_url': 'http:/localhost:5000',
            },
        }
    })
    ConfigManager().dump(config)

    with requests_mock.Mocker() as m:
        m.delete(
            'http://localhost:5000/api/tokens/current',
            status_code=401,
        )

        output = invoke_cli('registry', 'logout', env={'IDF_TOOLS_PATH': str(tmp_path)})

    assert 'Successfully logged out' in output.stdout
    if sys.version_info < (3, 10):
        assert 'Failed to revoke token from the registry' in output.stdout
    else:
        assert 'Failed to revoke token from the registry' in output.stderr


def test_logout_from_registry_no_revoke(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))
    config = Config.fromdict({
        'profiles': {
            'default': {
                'api_token': 'asdf',
            },
        }
    })
    ConfigManager().dump(config)

    output = invoke_cli(
        'registry',
        'logout',
        '--no-revoke',
        env={'IDF_TOOLS_PATH': str(tmp_path)},
    )

    assert 'Successfully logged out' in output.stdout
