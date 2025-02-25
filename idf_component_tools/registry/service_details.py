# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

"""Helper function to init API client"""

import typing as t

from idf_component_tools import ComponentManagerSettings
from idf_component_tools.config import ProfileItem, get_profile, get_registry_url, get_storage_urls

from .api_client import APIClient
from .multi_storage_client import MultiStorageClient


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
