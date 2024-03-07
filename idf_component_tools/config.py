# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import warnings
from typing import Any, Dict, Iterator, List
from typing import Optional as OptionalType
from typing import Tuple

import yaml
from schema import And, Optional, Or, Regex, Schema, SchemaError

from idf_component_tools.constants import COMPILED_FILE_RE, COMPILED_URL_RE
from idf_component_tools.errors import FatalError, ProfileNotValid
from idf_component_tools.messages import UserDeprecationWarning

from .build_system_tools import get_idf_version
from .constants import IDF_COMPONENT_REGISTRY_URL, IDF_COMPONENT_STORAGE_URL

DEFAULT_CONFIG_DIR = os.path.join('~', '.espressif')

CONFIG_SCHEMA = Schema(
    {
        Optional('profiles'): {
            str:
            # Use Or to allow either a None value or
            # a dictionary with specific keys and validation rules
            Or(
                None,
                {
                    Optional('registry_url'): Or('default', Regex(COMPILED_URL_RE)),
                    Optional('storage_url'): Or(
                        'default',
                        Or(Regex(COMPILED_URL_RE), Regex(COMPILED_FILE_RE)),
                        [Or(Regex(COMPILED_URL_RE), Regex(COMPILED_FILE_RE))],
                    ),
                    Optional('default_namespace'): And(str, len),
                    Optional('api_token'): And(str, len),
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
    return os.path.join(config_dir(), 'root_managed_components', f'idf{get_idf_version()}')


class ConfigError(FatalError):
    pass


class Config:
    def __init__(self, config: OptionalType[Dict] = None) -> None:
        self._config = config or {}

    def __getitem__(self, key: Any) -> Any:
        return self._config[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self._config[key] = value

    def __delitem__(self, key: Any) -> None:
        del self._config[key]

    def __len__(self) -> int:
        return len(self._config)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._config.items())

    def __contains__(self, item: Any) -> bool:
        return item in self._config

    @property
    def profiles(self) -> Dict:
        return self._config.setdefault('profiles', {})

    def validate(self) -> Config:
        try:
            self._config = CONFIG_SCHEMA.validate(self._config)
            return self
        except SchemaError as e:
            raise ConfigError(f'Config format is not valid:\n{e}')


class ConfigManager:
    def __init__(self, path=None):
        self.config_path = path or os.path.join(config_dir(), 'idf_component_manager.yml')

    def load(self) -> Config:
        """Loads config from disk"""
        if not os.path.isfile(self.config_path):
            return Config({})

        with open(self.config_path, encoding='utf-8') as f:
            try:
                return Config(yaml.safe_load(f.read())).validate()
            except yaml.YAMLError:
                raise ConfigError(
                    'Cannot parse config file. '
                    'Please check that\n\t{}\nis valid YAML file\n'.format(self.config_path)
                )

    def dump(self, config: Config) -> None:
        """Writes config to disk"""
        with open(self.config_path, mode='w', encoding='utf-8') as f:
            yaml.dump(data=dict(config.validate()), stream=f, encoding='utf-8', allow_unicode=True)


def get_api_url(url: str) -> str:
    url = url.rstrip('/')

    if url.endswith('/api'):
        return f'{url}/'

    return f'{url}/api/'


def replace_default_value(storage_urls: List[str]) -> List[str]:
    storage_urls_copy = list(storage_urls)
    for i, storage_url in enumerate(storage_urls_copy):
        if storage_url == 'default':
            storage_urls_copy[i] = IDF_COMPONENT_STORAGE_URL

    return storage_urls_copy


def component_registry_url(
    registry_profile: OptionalType[Dict[str, str]] = None,
) -> Tuple[OptionalType[str], OptionalType[List[str]]]:
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
                    '`storage_url` field may only be a string with one URL. '
                    'For multiple URLs, use list syntax'
                )
            storage_urls = [profile_storage_urls]
        else:
            raise ProfileNotValid(
                f'`storage_url` field should be string or list, not {storage_urls}'
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
