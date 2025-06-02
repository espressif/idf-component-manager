# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import typing as t
from pathlib import Path

from pydantic import (
    Discriminator,
    Tag,
    ValidationError,
    field_validator,
)
from ruamel.yaml import YAML, CommentedMap, YAMLError

from idf_component_tools.constants import (
    IDF_COMPONENT_REGISTRY_URL,
    IDF_COMPONENT_STORAGE_URL,
)
from idf_component_tools.errors import FatalError, NoSuchProfile
from idf_component_tools.utils import (
    Annotated,
    BaseModel,
    Literal,
    UrlField,
    UrlOrFileField,
    default_or_str_or_list_or_none_discriminator,
    default_or_str_or_none_discriminator,
    polish_validation_error,
    str_or_list_or_none_discriminator,
)

from .build_system_tools import get_idf_version
from .environment import ComponentManagerSettings

RegistryUrlField = Annotated[
    t.Union[
        Annotated[Literal['default'], Tag('__default__')],
        Annotated[UrlField, Tag('__str__')],
        Annotated[None, Tag('__none__')],
    ],
    Discriminator(
        default_or_str_or_none_discriminator,
    ),
]

StorageUrlField = Annotated[
    t.Union[
        Annotated[Literal['default'], Tag('__default__')],
        Annotated[UrlOrFileField, Tag('__str__')],
        Annotated[t.List[UrlOrFileField], Tag('__list__')],
        Annotated[None, Tag('__none__')],
    ],
    Discriminator(
        default_or_str_or_list_or_none_discriminator,
    ),
]
LocalStorageUrlField = Annotated[
    t.Union[
        Annotated[UrlOrFileField, Tag('__str__')],
        Annotated[t.List[UrlOrFileField], Tag('__list__')],
        Annotated[None, Tag('__none__')],
    ],
    Discriminator(
        str_or_list_or_none_discriminator,
    ),
]


class ProfileItem(BaseModel):
    registry_url: RegistryUrlField = None
    storage_url: StorageUrlField = None
    local_storage_url: LocalStorageUrlField = None
    default_namespace: str = None  # type: ignore
    api_token: t.Optional[str] = None

    @field_validator('registry_url')
    @classmethod
    def validate_registry_url(cls, v):
        if v == 'default' or not v:
            return IDF_COMPONENT_REGISTRY_URL

        return v

    @property
    def storage_urls(self) -> t.List[str]:
        _storage_urls: t.Set[str] = set()
        if isinstance(self.storage_url, list):
            return self.storage_url

        return [self.storage_url] if self.storage_url else []

    @property
    def local_storage_urls(self) -> t.List[str]:
        if isinstance(self.local_storage_url, list):
            return self.local_storage_url

        return [self.local_storage_url] if self.local_storage_url else []


class Config(BaseModel):
    profiles: t.Dict[str, t.Optional[ProfileItem]] = {}


def config_dir() -> Path:
    return Path(os.environ.get('IDF_TOOLS_PATH') or Path.home() / '.espressif')


def config_file() -> Path:
    return config_dir() / 'idf_component_manager.yml'


def root_managed_components_dir() -> Path:
    return config_dir() / 'root_managed_components' / f'idf{get_idf_version()}'


class ConfigError(FatalError):
    pass


class ConfigManager:
    def __init__(self, path=None):
        self.config_path = Path(path) if path else config_file()
        self._yaml = YAML()
        self._raw_data: CommentedMap = None  # Storage for CommentedMap from the config file

    # Lazy-load property
    @property
    def data(self) -> CommentedMap:
        if self._raw_data is None:
            self.load()
        return self._raw_data

    def load(self) -> Config:
        """Loads config from disk"""
        if not self.config_path.is_file():
            self._raw_data = CommentedMap()
            return Config()

        with open(self.config_path, encoding='utf-8') as f:
            try:
                self._raw_data = self._yaml.load(f) or CommentedMap()
                return self.validate(self._raw_data)
            except YAMLError:
                raise ConfigError(
                    f'Invalid config file: {self.config_path}\n'
                    f'Please check if the file is in valid YAML format'
                )
            except ConfigError as e:
                raise ConfigError(f'Invalid config file: {self.config_path}\n{e}')

    @classmethod
    def validate(cls, data: t.Any) -> Config:
        try:
            return Config.model_validate(data)
        except ValidationError as e:
            raise ConfigError(polish_validation_error(e))

    def dump(self, config: Config) -> None:
        """Writes config to disk"""

        # Update the original data with values from the config model
        self._update_data(config)

        # Ensure the directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, mode='w', encoding='utf-8') as f:
            self._yaml.dump(self.data, f)

    def _update_data(self, config: Config) -> None:
        """Update the CommentedMap with values from the Config model"""
        # Include None values to unset fields in the profile
        model_data = config.model_dump(exclude_none=False)
        profiles = self.data.get('profiles', CommentedMap())

        for profile_name, profile_values in model_data['profiles'].items():
            if profile_name in profiles:
                if profile_values is None:
                    profiles[profile_name] = None
                # Update existing profile
                else:
                    if profiles[profile_name] is None:
                        profiles[profile_name] = {}
                    for field_name, field_value in profile_values.items():
                        # Update values
                        profiles[profile_name][field_name] = field_value
            else:
                # Add new profile
                profiles[profile_name] = profile_values

        empty_profiles = []
        # Clean up subkeys with None values and collect empty profiles
        for profile_name, profile_values in profiles.items():
            if profile_values is not None:
                for field_name in [k for k, v in profile_values.items() if v is None]:
                    del profile_values[field_name]
                if not profile_values:
                    empty_profiles.append(profile_name)

        # Delete empty profiles outside the loop
        for profile_name in empty_profiles:
            del profiles[profile_name]

        self._raw_data['profiles'] = profiles


def get_profile(
    profile_name: t.Optional[str] = None,
    config_path: t.Optional[str] = None,
) -> ProfileItem:
    config_manager = ConfigManager(path=config_path)
    config = config_manager.load()
    _profile_name = ComponentManagerSettings().PROFILE or profile_name or 'default'

    if (
        _profile_name == 'default' and config.profiles.get(_profile_name) is None
    ) or not _profile_name:
        return ProfileItem()  # empty profile

    if _profile_name in config.profiles:
        return config.profiles[_profile_name] or ProfileItem()

    raise NoSuchProfile(
        f'Profile "{_profile_name}" not found in config file: {config_manager.config_path}'
    )


def get_registry_url(profile: t.Optional[ProfileItem] = None) -> str:
    """
    Env var > profile settings > default
    """
    if profile is None:
        profile = get_profile()

    return (
        ComponentManagerSettings().REGISTRY_URL
        or (profile.registry_url if profile else IDF_COMPONENT_REGISTRY_URL)
        or IDF_COMPONENT_REGISTRY_URL
    )


def get_storage_urls(profile: t.Optional[ProfileItem] = None) -> t.List[str]:
    """
    Env var > profile settings > default
    """
    if profile is None:
        profile = get_profile()

    storage_url_env = ComponentManagerSettings().STORAGE_URL  # fool mypy
    if storage_url_env:
        storage_urls = storage_url_env.split(';')
    else:
        storage_urls = profile.storage_urls or []

    res = []  # sequence matters, the first url goes first
    for url in storage_urls:
        url = url.strip()
        if url == 'default':
            _url = IDF_COMPONENT_STORAGE_URL
        else:
            _url = url

        if _url not in res:
            res.append(_url)
    return res
