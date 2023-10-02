# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
''' Helper function to init API client'''
import os
import warnings
from collections import namedtuple

from idf_component_manager.utils import print_info
from idf_component_tools.api_client import APIClient
from idf_component_tools.config import ConfigManager, component_registry_url
from idf_component_tools.constants import DEFAULT_NAMESPACE
from idf_component_tools.errors import FatalError, UserDeprecationWarning

ServiceDetails = namedtuple('ServiceDetails', ['client', 'namespace'])


class NamespaceError(FatalError):
    pass


class APITokenError(FatalError):
    pass


class NoSuchProfile(FatalError):
    pass


def get_namespace(profile, namespace=None):  # type: (dict[str, str], str | None) -> str
    if namespace:
        return namespace

    return profile.get('default_namespace', DEFAULT_NAMESPACE)


def get_token(profile, token_required=True):  # type: (dict[str, str], bool) -> str | None
    token = os.getenv('IDF_COMPONENT_API_TOKEN') or profile.get('api_token')

    if not token and token_required:
        raise APITokenError('Failed to get API Token from the config file')

    return token


def get_profile(
    profile_name,
    config_path=None,
):  # type: (str, str | None) -> dict[str, str] | None
    profile_name_env_deprecated = os.getenv('IDF_COMPONENT_SERVICE_PROFILE')

    if profile_name_env_deprecated:
        warnings.warn(
            'IDF_COMPONENT_SERVICE_PROFILE environment variable is deprecated. '
            'Please use IDF_COMPONENT_REGISTRY_PROFILE instead',
            category=UserDeprecationWarning,
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


def validate_profile(
    profile, profile_name, raise_on_missing=True
):  # type: (dict[str, str] | None, str, bool) -> None
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
    profile,  # type: dict[str,str] | None
    namespace=None,  # type: str | None
    token_required=True,
):  # type: (...) -> tuple[APIClient, str]
    if profile is None:
        profile = {}

    # Priorities:
    # Environment variables > profile value in `idf_component_manager.yml` file > built-in default
    registry_url, storage_url = component_registry_url(registry_profile=profile)

    # Priorities: CLI option > IDF_COMPONENT_NAMESPACE env variable > profile value > Default
    namespace = get_namespace(profile, namespace)

    # Priorities: IDF_COMPONENT_API_TOKEN env variable > profile value
    token = get_token(profile, token_required=token_required)

    client = APIClient(base_url=registry_url, storage_url=storage_url, auth_token=token)

    return ServiceDetails(client, namespace)


def service_details(
    namespace=None,  # type: str | None
    service_profile=None,  # type: str | None
    config_path=None,  # type: str | None
    token_required=True,
):  # type: (...) -> tuple[APIClient, str]
    profile_name = service_profile or 'default'
    profile = get_profile(profile_name, config_path=config_path)
    validate_profile(profile, profile_name)
    return service_details_for_profile(
        namespace=namespace, profile=profile, token_required=token_required
    )
