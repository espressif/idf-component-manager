import json
import os
import shutil
import tempfile
from io import open

from idf_component_manager.config import Config, ConfigError, ConfigManager
from pytest import raises


def test_config_validation():
    assert Config({}).validate()
    assert Config(
        {
            'profiles': {
                'default': {
                    'service_url': 'default',
                },
                'in_office': {
                    'service_url': 'http://api.localserver.local:5000/',
                    'api_token': 'asdf',
                    'default_namespace': 'asdf',
                }
            }
        }).validate()

    with raises(ConfigError):
        Config('asdf').validate()

    with raises(ConfigError):
        Config({
            'profiles': {
                'in_office': {
                    'service_url': 'pptp://api.localserver.local:5000/'
                },
            }
        }).validate()


def test_load_config():
    tempdir = tempfile.mkdtemp()
    config_path = os.path.join(tempdir, 'idf_component_manager.yml')
    config = Config(
        {
            'profiles': {
                'default': {
                    'service_url': 'default',
                },
                'in_office': {
                    'service_url': 'http://api.localserver.local:5000/',
                    'api_token': 'asdf',
                    'default_namespace': 'asdf',
                }
            }
        })

    # Use json representation to compare equality of nested dictionaries
    config_json = json.dumps(dict(config), sort_keys=True, indent=2)

    try:

        manager = ConfigManager(path=config_path)
        # save to file
        manager.dump(config)

        with open(config_path, mode='r', encoding='utf-8') as file:
            assert file.readline().startswith('profiles:')

        # load from file
        loaded_config = manager.load()

        assert loaded_config.profiles['in_office']['default_namespace'] == 'asdf'
        assert config_json == json.dumps(dict(loaded_config), sort_keys=True, indent=2)

    finally:
        shutil.rmtree(tempdir)
