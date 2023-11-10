# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import warnings
from io import open

import yaml
from schema import And, Optional, Or, Regex, Schema, SchemaError
from six import string_types

from idf_component_tools.constants import COMPILED_FILE_RE, COMPILED_URL_RE
from idf_component_tools.errors import FatalError, ProfileNotValid
from idf_component_tools.messages import UserDeprecationWarning

from .build_system_tools import get_idf_version
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
                    Optional('storage_url'): Or(
                        'default',
                        Or(Regex(COMPILED_URL_RE), Regex(COMPILED_FILE_RE)),
                        [Or(Regex(COMPILED_URL_RE), Regex(COMPILED_FILE_RE))],
                    ),
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


def root_managed_components_dir():
    return os.path.join(config_dir(), 'root_managed_components', 'idf{}'.format(get_idf_version()))


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


def replace_default_value(storage_urls):  # type: (list[str]) -> list[str]
    storage_urls_copy = list(storage_urls)
    for i, storage_url in enumerate(storage_urls_copy):
        if storage_url == 'default':
            storage_urls_copy[i] = IDF_COMPONENT_STORAGE_URL

    return storage_urls_copy


def component_registry_url(
    registry_profile=None,
):  # type: (dict[str, str] | None) -> tuple[str | None, list[str] | None]
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
        storage_urls = None
        if env_storage_url:
            storage_urls = env_storage_url.split(';')
            storage_urls = replace_default_value(storage_urls)

        return env_registry_api_url, storage_urls

    if registry_profile is None:
        registry_profile = {}

    storage_urls = None
    profile_storage_urls = registry_profile.get('storage_url')
    if profile_storage_urls and profile_storage_urls != 'default':
        if isinstance(profile_storage_urls, list):
            storage_urls = replace_default_value(profile_storage_urls)
        elif isinstance(profile_storage_urls, str):
            if profile_storage_urls.find(';') != -1:
                raise ProfileNotValid(
                    '`storage_url` field may only be a string with one URL. For multiple URLs, use list syntax'
                )
            storage_urls = [profile_storage_urls]
        else:
            raise ProfileNotValid(
                '`storage_url` field should be string or list, not {}'.format(storage_urls)
            )

    registry_url = None
    profile_registry_url = registry_profile.get('registry_url')
    if profile_registry_url and profile_registry_url != 'default':
        registry_url = profile_registry_url

    if storage_urls and not registry_url:
        return None, storage_urls

    if not registry_url:
        registry_url = IDF_COMPONENT_REGISTRY_URL

        if not storage_urls:
            storage_urls = [IDF_COMPONENT_STORAGE_URL]

    return get_api_url(registry_url), storage_urls
