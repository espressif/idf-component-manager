# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import typing as t
from pathlib import Path

import yaml
from pydantic import (
    ValidationError,
    field_validator,
)

from idf_component_tools.constants import (
    IDF_COMPONENT_REGISTRY_URL,
)
from idf_component_tools.errors import FatalError
from idf_component_tools.utils import (
    BaseModel,
    Literal,
    UrlField,
    UrlOrFileField,
    validation_error_to_str,
)

from .build_system_tools import get_idf_version

RegistryUrlField = t.Union[
    Literal['default'],
    UrlField,
    None,
]
StorageUrlField = t.Union[
    Literal['default'],
    UrlOrFileField,
    t.List[UrlOrFileField],
    None,
]
LocalStorageUrlField = t.Union[
    UrlOrFileField,
    t.List[UrlOrFileField],
    None,
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


def root_managed_components_dir() -> Path:
    return config_dir() / 'root_managed_components' / f'idf{get_idf_version()}'


class ConfigError(FatalError):
    pass


class ConfigManager:
    def __init__(self, path=None):
        self.config_path = Path(path) if path else (config_dir() / 'idf_component_manager.yml')

    def load(self) -> Config:
        """Loads config from disk"""
        if not self.config_path.is_file():
            return Config()

        with open(self.config_path, encoding='utf-8') as f:
            try:
                return self.validate(yaml.safe_load(f.read()))
            except yaml.YAMLError:
                raise ConfigError(
                    'Cannot parse config file. '
                    'Please check that\n\t{}\nis valid YAML file\n'.format(self.config_path)
                )

    @classmethod
    def validate(cls, data: t.Any) -> Config:
        try:
            return Config.model_validate(data)
        except ValidationError as e:
            raise ConfigError('\n'.join([validation_error_to_str(err) for err in e.errors()]))

    def dump(self, config: Config) -> None:
        """Writes config to disk"""

        # Make sure that directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, mode='w', encoding='utf-8') as f:
            yaml.dump(data=config.model_dump(), stream=f, encoding='utf-8', allow_unicode=True)
