# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

"""Helper function to init API client"""

import typing as t

from idf_component_tools import ComponentManagerSettings
from idf_component_tools.config import ConfigManager, ProfileItem
from idf_component_tools.constants import (
    IDF_COMPONENT_REGISTRY_URL,
    IDF_COMPONENT_STORAGE_URL,
)
from idf_component_tools.errors import FatalError

from .api_client import APIClient
from .multi_storage_client import MultiStorageClient


class NoSuchProfile(FatalError):
    pass


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
        f'Profile "{profile_name}" not found in config file: {config_manager.config_path}'
    )


def get_registry_url(profile: t.Optional[ProfileItem] = None) -> str:
    """
    Env var > profile settings > default
    """
    return (
        ComponentManagerSettings().REGISTRY_URL
        or (profile.registry_url if profile else IDF_COMPONENT_REGISTRY_URL)
        or IDF_COMPONENT_REGISTRY_URL
    )


def get_storage_urls(profile: t.Optional[ProfileItem] = None) -> t.List[str]:
    """
    Env var > profile settings > default
    """
    storage_url_env = ComponentManagerSettings().STORAGE_URL
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
    registry_url: t.Optional[str] = None,
    *,
    namespace: t.Optional[str] = None,
    profile_name: t.Optional[str] = None,
    config_path: t.Optional[str] = None,
    profile: t.Optional[ProfileItem] = None,
) -> APIClient:
    """
    Api Client should be used when you're "writing" to the registry,

    For example, when you need to upload, validate, or delete a component.

    The priority of which internal client is using is:

    - registry_url, if specified
    - get_registry_url()
    """
    if profile is None:
        profile = get_profile(profile_name, config_path)

    return APIClient(
        registry_url=registry_url or get_registry_url(profile),
        api_token=ComponentManagerSettings().API_TOKEN or (profile.api_token if profile else None),
        default_namespace=namespace or (profile.default_namespace if profile else None),
    )


def get_storage_client(
    registry_url: t.Optional[str] = None,
    *,
    storage_urls: t.Optional[t.List[str]] = None,
    local_storage_urls: t.Optional[t.List[str]] = None,
    namespace: t.Optional[str] = None,
    profile_name: t.Optional[str] = None,
    config_path: t.Optional[str] = None,
    profile: t.Optional[ProfileItem] = None,
    local_first_mode: bool = True,
) -> MultiStorageClient:
    """
    Client should be used when you're "reading" from the registry,

    For example, when you need to download a component or get its metadata.

    The priority of which internal client is using is:

    - registry_storage_url get from api of `registry_url`, if specified
    - local_storage_urls defined in the profile
    - get_storage_urls()
    - get_registry_url()
    """
    if profile is None:
        profile = get_profile(profile_name, config_path)

    _registry_url = registry_url or get_registry_url(profile)

    _storage_urls = get_storage_urls(profile) if profile else []
    if storage_urls:
        _storage_urls += storage_urls

    _local_storage_urls = (profile.local_storage_urls or []) if profile else []
    if local_storage_urls:
        _local_storage_urls += local_storage_urls

    return MultiStorageClient(
        registry_url=_registry_url,
        storage_urls=_storage_urls,
        local_storage_urls=_local_storage_urls,
        api_token=ComponentManagerSettings().API_TOKEN or (profile.api_token if profile else None),
        default_namespace=namespace or (profile.default_namespace if profile else None),
        local_first_mode=local_first_mode,
    )
