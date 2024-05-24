# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

"""Helper function to init API client"""

import os
import typing as t
import warnings

from idf_component_tools.config import ConfigManager, ServiceProfileItem
from idf_component_tools.constants import (
    IDF_COMPONENT_REGISTRY_URL,
    IDF_COMPONENT_STORAGE_URL,
)
from idf_component_tools.errors import FatalError
from idf_component_tools.messages import UserDeprecationWarning

from .api_client import APIClient
from .multi_storage_client import MultiStorageClient


class NoSuchProfile(FatalError):
    pass


def get_profile(
    profile_name: t.Optional[str] = None,
    config_path: t.Optional[str] = None,
) -> t.Optional[ServiceProfileItem]:
    profile_name_env_deprecated = os.getenv('IDF_COMPONENT_SERVICE_PROFILE')

    if profile_name_env_deprecated:
        warnings.warn(
            'IDF_COMPONENT_SERVICE_PROFILE environment variable is deprecated. '
            'Please use IDF_COMPONENT_REGISTRY_PROFILE instead',
            UserDeprecationWarning,
        )

    profile_name_env = os.getenv('IDF_COMPONENT_REGISTRY_PROFILE')

    if profile_name_env and profile_name_env_deprecated:
        warnings.warn(
            'Both IDF_COMPONENT_SERVICE_PROFILE and IDF_COMPONENT_REGISTRY_PROFILE '
            'environment variables are defined. The value of IDF_COMPONENT_REGISTRY_PROFILE '
            'is used.'
        )

    config = ConfigManager(path=config_path).load()

    _profile_name = profile_name_env or profile_name_env_deprecated or profile_name
    if (
        _profile_name == 'default' and config.profiles.get(_profile_name) is None
    ) or not _profile_name:
        return ServiceProfileItem()  # empty profile

    if _profile_name in config.profiles:
        return config.profiles[_profile_name] or ServiceProfileItem()

    return None


def get_registry_url(profile: t.Optional[ServiceProfileItem] = None) -> str:
    """
    Env var > profile settings > default
    """
    registry_url_env_deprecated = os.getenv('DEFAULT_COMPONENT_SERVICE_URL')

    if registry_url_env_deprecated:
        warnings.warn(
            'DEFAULT_COMPONENT_SERVICE_URL environment variable pointing to the '
            'registy API is deprecated. Set component registry URL to IDF_COMPONENT_REGISTRY_URL',
            UserDeprecationWarning,
        )

    registry_url_env = os.getenv('IDF_COMPONENT_REGISTRY_URL')
    if registry_url_env and registry_url_env_deprecated:
        warnings.warn(
            'Both DEFAULT_COMPONENT_SERVICE_URL and IDF_COMPONENT_REGISTRY_URL '
            'environment variables are defined. The value of IDF_COMPONENT_REGISTRY_URL is used.'
        )

    return (
        registry_url_env
        or registry_url_env_deprecated
        or (profile.registry_url if profile else IDF_COMPONENT_REGISTRY_URL)
        or IDF_COMPONENT_REGISTRY_URL
    )


def get_storage_urls(profile: t.Optional[ServiceProfileItem] = None) -> t.List[str]:
    """
    Env var > profile settings > default
    """
    storage_url_env = os.getenv('IDF_COMPONENT_STORAGE_URL')
    if storage_url_env:
        _storage_urls = [url.strip() for url in storage_url_env.split(';') if url.strip()]
    else:
        _storage_urls = profile.storage_urls if profile else []

    res = []  # sequence matters, the first url goes first
    for url in _storage_urls:
        if url == 'default':
            _url = IDF_COMPONENT_STORAGE_URL
        else:
            _url = url

        if _url not in res:
            res.append(_url)

    return res


def get_api_client(
    namespace: t.Optional[str] = None,
    service_profile: t.Optional[str] = None,
    config_path: t.Optional[str] = None,
    profile: t.Optional[ServiceProfileItem] = None,
) -> APIClient:
    """
    Api Client should be used when you're "writing" to the registry,

    For example, when you need to upload, validate, or delete a component.
    """
    if profile is None:
        profile = get_profile(service_profile, config_path)

    if service_profile and profile is None:
        raise NoSuchProfile(
            f'Profile "{service_profile}" not found in the idf_component_manager.yml config file'
        )

    return APIClient(
        registry_url=get_registry_url(profile),
        api_token=os.getenv('IDF_COMPONENT_API_TOKEN') or (profile.api_token if profile else None),
        default_namespace=namespace or (profile.default_namespace if profile else None),
    )


def get_storage_client(
    namespace: t.Optional[str] = None,
    service_profile: t.Optional[str] = None,
    config_path: t.Optional[str] = None,
    profile: t.Optional[ServiceProfileItem] = None,
    local_first_mode: bool = True,
) -> MultiStorageClient:
    """
    Client should be used when you're "reading" from the registry,

    For example, when you need to download a component or get its metadata.
    """
    if profile is None:
        profile = get_profile(service_profile, config_path)

    if service_profile and profile is None:
        raise NoSuchProfile(
            f'Profile "{service_profile}" not found in the idf_component_manager.yml config file'
        )

    return MultiStorageClient(
        registry_url=get_registry_url(profile),
        storage_urls=get_storage_urls(profile) if profile else [],
        local_storage_urls=(profile.local_storage_urls or []) if profile else [],
        api_token=os.getenv('IDF_COMPONENT_API_TOKEN') or (profile.api_token if profile else None),
        default_namespace=namespace or (profile.default_namespace if profile else None),
        local_first_mode=local_first_mode,
    )
