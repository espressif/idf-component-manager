# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


from idf_component_tools.config import Config, ConfigManager


def test_config_path(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    result = invoke_cli('config', 'path')

    assert result.exit_code == 0
    assert str(tmp_path) in result.stdout


def test_config_list(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    config = Config.fromdict({
        'profiles': {
            'default': {
                'registry_url': 'https://components.espressif.com',
                'default_namespace': 'espressif',
                'api_token': 'some_token',
            },
            'some_other_profile': {'aaa': 'bbb'},
            'empty_profile': {},
        }
    })
    ConfigManager().dump(config)

    result = invoke_cli('config', 'list')

    assert result.exit_code == 0

    # Expected output
    expected_output = (
        '\nProfile: default\n'
        '\tRegistry Url        : https://components.espressif.com/\n'
        '\tDefault Namespace   : espressif\n'
        '\tApi Token           : ***hidden***\n'
    )

    # Compare the raw CLI output
    assert result.output == expected_output


def test_config_set(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    config = Config.fromdict({
        'profiles': {
            'test': {
                'api_token': 'token',
                'registry_url': 'https://components.espressif.com',
                'default_namespace': 'espressif',
                'local_storage_url': 'https://some_url',
                'storage_url': 'https://some_url',
            },
        }
    })
    ConfigManager().dump(config)

    result = invoke_cli(
        'config',
        'set',
        '--profile',
        'test',
        '--registry-url',
        'https://some_url',
        '--storage-url',
        'https://some_another_url',
        '--storage-url',
        'https://some_another_url1',
        '--local-storage-url',
        'https://some_another_url',
        '--api-token',
        'another_token',
        '--default-namespace',
        'test',
    )
    assert result.exit_code == 0
    assert "Profile 'test' updated with provided values." in result.output
    config = ConfigManager().load()
    profiles = config.profiles
    assert 'test' in profiles
    assert profiles['test'].registry_url == 'https://some_url/'
    assert profiles['test'].storage_url == [
        'https://some_another_url/',
        'https://some_another_url1/',
    ]
    assert profiles['test'].local_storage_url == ['https://some_another_url/']
    assert profiles['test'].default_namespace == 'test'
    assert profiles['test'].api_token == 'another_token'


def test_config_set_without_arguments(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    result = invoke_cli('config', 'set', '--profile', 'test')

    assert result.exit_code == 1
    assert 'Please provide a parameter you want to change.' in str(result.exception)


def test_config_set_not_existing_profile(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    result = invoke_cli(
        'config',
        'set',
        '--profile',
        'test',
        '--registry-url',
        'https://some_url',
        '--default-namespace',
        'test',
    )

    assert result.exit_code == 0
    assert "Profile 'test' updated with provided values." in result.output
    config = ConfigManager().load()
    profiles = config.profiles
    assert 'test' in profiles
    default_profile = profiles['test']
    assert default_profile.registry_url == 'https://some_url/'
    assert default_profile.default_namespace == 'test'


def test_config_unset(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    config = Config.fromdict({
        'profiles': {
            'test': {
                'api_token': 'token',
                'registry_url': 'https://components.espressif.com',
                'default_namespace': 'espressif',
                'local_storage_url': 'https://some_url',
                'storage_url': 'https://some_url',
            },
        }
    })
    ConfigManager().dump(config)

    result = invoke_cli(
        'config',
        'unset',
        '--profile',
        'test',
        '--registry-url',
        '--storage-url',
        '--local-storage-url',
        '--default-namespace',
    )

    assert result.exit_code == 0
    assert (
        'Successfully removed registry_url, storage_url, local_storage_url, default_namespace from the profile "test".\n'
        in result.output
    )
    config = ConfigManager().load()
    assert config.profiles['test'].registry_url is None
    assert config.profiles['test'].storage_url is None
    assert config.profiles['test'].local_storage_url is None
    assert config.profiles['test'].default_namespace is None
    assert config.profiles['test'].api_token is not None


def test_config_unset_all(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    config = Config.fromdict({
        'profiles': {
            'test': {
                'api_token': 'token',
                'registry_url': 'https://components.espressif.com',
                'default_namespace': 'espressif',
                'local_storage_url': 'https://some_url',
                'storage_url': 'https://some_url',
            },
            'test1': {
                'api_token': 'token1',
            },
        }
    })
    ConfigManager().dump(config)

    result = invoke_cli(
        'config',
        'unset',
        '--profile',
        'test',
        '--all',
    )

    assert result.exit_code == 0
    assert 'Profile "test" was completely removed from the config file.\n' in result.output
    config = ConfigManager().load()
    assert 'test' not in config.profiles
    assert 'test1' in config.profiles


def test_unset_not_existing_profile(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    result = invoke_cli(
        'config',
        'unset',
        '--profile',
        'test',
        '--all',
    )

    assert result.exit_code == 1
    assert "Profile 'test' does not exist." in str(result.exception)


def test_config_unset_without_arguments(monkeypatch, tmp_path, invoke_cli):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    result = invoke_cli('config', 'unset', '--profile', 'test')

    assert result.exit_code == 1
    assert 'Please provide at least one field to unset or use --all to remove the profile.' in str(
        result.exception
    )
