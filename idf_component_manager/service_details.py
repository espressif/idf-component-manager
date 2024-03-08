# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

"""Helper function to init API client"""

import os
import typing as t
import warnings
from collections import namedtuple
from functools import lru_cache

from idf_component_manager.utils import print_info
from idf_component_tools.config import ConfigManager, component_registry_url
from idf_component_tools.constants import DEFAULT_NAMESPACE
from idf_component_tools.errors import FatalError
from idf_component_tools.messages import UserDeprecationWarning
from idf_component_tools.registry.api_client import APIClient
from idf_component_tools.registry.multi_storage_client import MultiStorageClient

ServiceDetails = namedtuple(
    'ServiceDetails', ['registry_url', 'storage_urls', 'token', 'namespace']
)


class NamespaceError(FatalError):
    pass


class APITokenError(FatalError):
    pass


class NoSuchProfile(FatalError):
    pass


def get_namespace(profile: t.Dict[str, str], namespace: t.Optional[str] = None) -> str:
    if namespace:
        return namespace

    return profile.get('default_namespace', DEFAULT_NAMESPACE)


def get_token(profile: t.Dict[str, str], token_required: bool = True) -> t.Optional[str]:
    token = os.getenv('IDF_COMPONENT_API_TOKEN') or profile.get('api_token')

    if not token and token_required:
        raise APITokenError('Failed to get API Token from the config file')

    return token


def get_profile(
    profile_name: str = '',
    config_path: t.Optional[str] = None,
) -> t.Optional[t.Dict[str, str]]:
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
    try:
        profile = config.profiles[profile_name_env or profile_name_env_deprecated or profile_name]
        return {} if profile is None else profile
    except KeyError:
        if profile_name == 'default':
            return {}
        return None


def get_component_registry_url_with_profile(
    config_path: t.Optional[str] = None,
) -> t.Tuple[t.Optional[str], t.Optional[t.List[str]]]:
    profile = get_profile(config_path=config_path)
    return component_registry_url(profile)


@lru_cache()
def get_storage_urls(
    registry_url: str,
):
    client = APIClient(base_url=registry_url)
    storage_urls = [client.api_information()['components_base_url']]
    return storage_urls


def get_registry_storage_urls(
    registry_profile: t.Optional[t.Dict[str, str]] = None,
    storage_required: bool = False,
):
    registry_url, storage_urls = component_registry_url(registry_profile)

    if storage_required and registry_url and not storage_urls:
        storage_urls = get_storage_urls(registry_url)

    return registry_url, storage_urls


def _load_service_profile_details(
    namespace: t.Optional[str] = None,
    service_profile: t.Optional[str] = None,
    config_path: t.Optional[str] = None,
    token_required: bool = True,
    raise_on_missing_profile: bool = True,
    storage_required: bool = False,
) -> ServiceDetails:
    profile_name = service_profile or 'default'
    profile = get_profile(profile_name, config_path)
    validate_profile(profile, profile_name, raise_on_missing_profile)

    return service_details_for_profile(profile, namespace, token_required, storage_required)


def validate_profile(
    profile: t.Optional[t.Dict[str, str]], profile_name: str, raise_on_missing: bool = True
) -> None:
    if profile:
        print_info(
            'Selected profile "{}" from the idf_component_manager.yml config file'.format(
                profile_name
            )
        )
    elif raise_on_missing and (profile_name != 'default' and profile is None):
        raise NoSuchProfile(
            'Profile "{}" not found in the idf_component_manager.yml config file'.format(
                profile_name
            )
        )


def service_details_for_profile(
    profile: t.Optional[t.Dict[str, str]],
    namespace: t.Optional[str] = None,
    token_required: bool = True,
    storage_required: bool = False,
) -> ServiceDetails:
    if profile is None:
        profile = {}

    # Priorities:
    # Environment variables > profile value in `idf_component_manager.yml` file > built-in default
    registry_url, storage_urls = get_registry_storage_urls(
        registry_profile=profile, storage_required=storage_required
    )

    # Priorities: CLI option > IDF_COMPONENT_NAMESPACE env variable > profile value > Default
    namespace = get_namespace(profile, namespace)

    # Priorities: IDF_COMPONENT_API_TOKEN env variable > profile value
    token = get_token(profile, token_required=token_required)

    return ServiceDetails(registry_url, storage_urls, token, namespace)


def get_api_client(
    namespace: t.Optional[str] = None,
    service_profile: t.Optional[str] = None,
    config_path: t.Optional[str] = None,
    token_required: bool = True,
    raise_on_missing_profile=True,
) -> t.Tuple[APIClient, str]:
    service_details = _load_service_profile_details(
        namespace, service_profile, config_path, token_required, raise_on_missing_profile
    )

    client = APIClient(base_url=service_details.registry_url, auth_token=service_details.token)

    return client, service_details.namespace


def get_storage_client(
    namespace: t.Optional[str] = None,
    service_profile: t.Optional[str] = None,
    config_path: t.Optional[str] = None,
    raise_on_missing_profile=True,
) -> t.Tuple[MultiStorageClient, str]:
    service_details = _load_service_profile_details(
        namespace,
        service_profile,
        config_path,
        token_required=False,
        storage_required=True,
        raise_on_missing_profile=raise_on_missing_profile,
    )

    client = MultiStorageClient(storage_urls=service_details.storage_urls)

    return client, service_details.namespace
