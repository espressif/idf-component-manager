# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import warnings
from io import open

import yaml
from schema import And, Optional, Or, Regex, Schema, SchemaError
from six import string_types

from idf_component_tools.constants import COMPILED_URL_RE
from idf_component_tools.errors import FatalError
from idf_component_tools.messages import UserDeprecationWarning

from .constants import IDF_COMPONENT_REGISTRY_URL, IDF_COMPONENT_STORAGE_URL

try:
    from typing import Any, Iterator, Tuple
except ImportError:
    pass

DEFAULT_CONFIG_DIR = os.path.join('~', '.espressif')

CONFIG_SCHEMA = Schema(
    {
        Optional('profiles'): {
            Or(*string_types):
            # Use Or to allow either a None value or a dictionary with specific keys and validation rules
            Or(
                None,
                {
                    Optional('registry_url'): Or('default', Regex(COMPILED_URL_RE)),
                    Optional('default_namespace'): And(Or(*string_types), len),
                    Optional('api_token'): And(Or(*string_types), len),
                    # allow any other keys that may be introduced in future versions
                    Optional(str): object,
                },
            ),
        },
        # allow any other keys that may be introduced in future versions
        Optional(str): object,
    }
)


def config_dir():
    return os.environ.get('IDF_TOOLS_PATH') or os.path.expanduser(DEFAULT_CONFIG_DIR)


class ConfigError(FatalError):
    pass


class Config(object):
    def __init__(self, config=None):  # type: (dict | None) -> None
        self._config = config or {}

    def __getitem__(self, key):  # type: (Any) -> Any
        return self._config[key]

    def __setitem__(self, key, value):  # type: (Any, Any) -> None
        self._config[key] = value

    def __delitem__(self, key):  # type: (Any) -> None
        del self._config[key]

    def __len__(self):  # type: () -> int
        return len(self._config)

    def __iter__(self):  # type: () -> Iterator[Any]
        return iter(self._config.items())

    def __contains__(self, item):  # type: (Any) -> bool
        return item in self._config

    @property
    def profiles(self):  # type: () -> dict
        return self._config.setdefault('profiles', {})

    def validate(self):  # type: () -> Config
        try:
            self._config = CONFIG_SCHEMA.validate(self._config)
            return self
        except SchemaError as e:
            raise ConfigError('Config format is not valid:\n{}'.format(str(e)))


class ConfigManager(object):
    def __init__(self, path=None):
        self.config_path = path or os.path.join(config_dir(), 'idf_component_manager.yml')

    def load(self):  # type: () -> Config
        """Loads config from disk"""
        if not os.path.isfile(self.config_path):
            return Config({})

        with open(self.config_path, mode='r', encoding='utf-8') as f:
            try:
                return Config(yaml.safe_load(f.read())).validate()
            except yaml.YAMLError:
                raise ConfigError(
                    'Cannot parse config file. Please check that\n\t{}\nis valid YAML file\n'.format(
                        self.config_path
                    )
                )

    def dump(self, config):  # type: (Config) -> None
        """Writes config to disk"""
        with open(self.config_path, mode='w', encoding='utf-8') as f:
            yaml.dump(data=dict(config.validate()), stream=f, encoding='utf-8', allow_unicode=True)


def get_api_url(url):  # type: (str) -> str
    url = url.rstrip('/')

    if url.endswith('/api'):
        return '{}/'.format(url)

    return '{}/api/'.format(url)


def component_registry_url(
    registry_profile=None,
):  # type: (dict[str, str] | None) -> tuple[str | None, str | None]
    """
    Returns registry API endpoint and static files URLs.

    Priorities:
    Environment variables > profile value in `idf_component_manager.yml` file > built-in default

    If storage URL is configured it will always be used for downloads of components
    """

    env_registry_url = os.getenv('IDF_COMPONENT_REGISTRY_URL')
    env_registry_api_url = os.getenv('DEFAULT_COMPONENT_SERVICE_URL')

    if env_registry_api_url:
        warnings.warn(
            'DEFAULT_COMPONENT_SERVICE_URL environment variable pointing to the '
            'registy API is deprecated. Set component registry URL to IDF_COMPONENT_REGISTRY_URL',
            UserDeprecationWarning,
        )

    if env_registry_url and env_registry_api_url:
        warnings.warn(
            'Both DEFAULT_COMPONENT_SERVICE_URL and IDF_COMPONENT_REGISTRY_URL '
            'environment variables are defined. The value of IDF_COMPONENT_REGISTRY_URL is used.'
        )

    if env_registry_url:
        env_registry_api_url = get_api_url(env_registry_url)

    env_storage_url = os.getenv('IDF_COMPONENT_STORAGE_URL')

    if env_registry_api_url or env_storage_url:
        return env_registry_api_url, env_storage_url

    if registry_profile is None:
        registry_profile = {}

    storage_url = None
    profile_storage_url = registry_profile.get('storage_url')
    if profile_storage_url and profile_storage_url != 'default':
        storage_url = profile_storage_url

    registry_url = None
    profile_registry_url = registry_profile.get('registry_url')
    if profile_registry_url and profile_registry_url != 'default':
        registry_url = profile_registry_url

    if storage_url and not registry_url:
        return None, storage_url

    if not registry_url:
        registry_url = IDF_COMPONENT_REGISTRY_URL

        if not storage_url:
            storage_url = IDF_COMPONENT_STORAGE_URL

    return get_api_url(registry_url), storage_url
