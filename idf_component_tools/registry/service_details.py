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
) -> t.Optional[ProfileItem]:
    config = ConfigManager(path=config_path).load()
    _profile_name = ComponentManagerSettings().PROFILE or profile_name

    if (
        _profile_name == 'default' and config.profiles.get(_profile_name) is None
    ) or not _profile_name:
        return ProfileItem()  # empty profile

    if _profile_name in config.profiles:
        return config.profiles[_profile_name] or ProfileItem()

    return None


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
    namespace: t.Optional[str] = None,
    profile_name: t.Optional[str] = None,
    config_path: t.Optional[str] = None,
    profile: t.Optional[ProfileItem] = None,
) -> APIClient:
    """
    Api Client should be used when you're "writing" to the registry,

    For example, when you need to upload, validate, or delete a component.
    """
    if profile is None:
        profile = get_profile(profile_name, config_path)

    if profile_name and profile is None:
        raise NoSuchProfile(
            f'Profile "{profile_name}" not found in the idf_component_manager.yml config file'
        )

    return APIClient(
        registry_url=get_registry_url(profile),
        api_token=ComponentManagerSettings().API_TOKEN or (profile.api_token if profile else None),
        default_namespace=namespace or (profile.default_namespace if profile else None),
    )


def get_storage_client(
    namespace: t.Optional[str] = None,
    profile_name: t.Optional[str] = None,
    config_path: t.Optional[str] = None,
    profile: t.Optional[ProfileItem] = None,
    local_first_mode: bool = True,
) -> MultiStorageClient:
    """
    Client should be used when you're "reading" from the registry,

    For example, when you need to download a component or get its metadata.
    """
    if profile is None:
        profile = get_profile(profile_name, config_path)

    if profile_name and profile is None:
        raise NoSuchProfile(
            f'Profile "{profile_name}" not found in the idf_component_manager.yml config file'
        )

    return MultiStorageClient(
        registry_url=get_registry_url(profile),
        storage_urls=get_storage_urls(profile) if profile else [],
        local_storage_urls=(profile.local_storage_urls or []) if profile else [],
        api_token=ComponentManagerSettings().API_TOKEN or (profile.api_token if profile else None),
        default_namespace=namespace or (profile.default_namespace if profile else None),
        local_first_mode=local_first_mode,
    )
