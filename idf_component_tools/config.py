import os
from io import open

import yaml
from schema import And, Optional, Or, Regex, Schema, SchemaError
from six import string_types

from idf_component_tools.constants import COMPILED_URL_RE
from idf_component_tools.errors import FatalError

DEFAULT_CONFIG_DIR = os.path.join('~', '.espressif')
CONFIG_DIR = os.environ.get('IDF_TOOLS_PATH') or os.path.expanduser(DEFAULT_CONFIG_DIR)

CONFIG_SCHEMA = Schema(
    {
        Optional('profiles'): {
            Or(*string_types): {
                Optional('service_url'): Or('default', Regex(COMPILED_URL_RE)),
                Optional('default_namespace'): And(Or(*string_types), len),
                Optional('api_token'): And(Or(*string_types), len)
            }
        }
    })


class ConfigError(FatalError):
    pass


class Config(object):
    def __init__(self, config=None):
        self._config = config or {}

    def __iter__(self):
        return iter(self._config.items())

    @property
    def profiles(self):
        return self._config.setdefault('profiles', {})

    def validate(self):
        try:
            self._config = CONFIG_SCHEMA.validate(self._config)
            return self
        except SchemaError as e:
            raise ConfigError('Config format is not valid:\n%s' % str(e))


class ConfigManager(object):
    def __init__(self, path=None):
        self.config_path = path or os.path.join(CONFIG_DIR, 'idf_component_manager.yml')

    def load(self):  # type: () -> Config
        """Loads config from disk"""
        if not os.path.isfile(self.config_path):
            return Config({}).validate()

        with open(self.config_path, mode='r', encoding='utf-8') as f:
            try:
                return Config(yaml.safe_load(f.read()))
            except yaml.YAMLError:
                raise ConfigError(
                    'Cannot parse config file. Please check that\n\t%s\nis valid YAML file\n' % self.config_path)

    def dump(self, config):  # type: (Config) -> None
        """Writes config to disk"""
        with open(self.config_path, mode='w', encoding='utf-8') as f:
            yaml.dump(data=dict(config.validate()), stream=f, encoding='utf-8', allow_unicode=True)
