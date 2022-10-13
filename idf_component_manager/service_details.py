# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
''' Helper function to init API client'''
import os
from collections import namedtuple

from idf_component_manager.utils import print_info
from idf_component_tools.api_client import APIClient
from idf_component_tools.config import ConfigManager, component_registry_url
from idf_component_tools.errors import FatalError

ServiceDetails = namedtuple('ServiceDetails', ['client', 'namespace'])


class NamespaceError(FatalError):
    pass


class APITokenError(FatalError):
    pass


class NoSuchProfile(FatalError):
    pass


def get_namespace(profile, namespace=None):  # type: (dict[str, str], str | None) -> str
    namespace = namespace or profile.get('default_namespace')

    if not namespace:
        raise NamespaceError('Failed to get namespace from the config file')

    return namespace


def get_token(profile):  # type: (dict[str, str]) -> str
    token = os.getenv('IDF_COMPONENT_API_TOKEN') or profile.get('api_token')

    if not token:
        raise APITokenError('Failed to get API Token from the config file')

    return token


def get_profile(config_path=None, profile_name=None):  # type: (str | None, str | None) -> dict[str, str]
    config = ConfigManager(path=config_path).load()
    profile = config.profiles.get(profile_name, {})
    return profile


def create_api_client(
        registry_url=None, storage_url=None, token=None):  # type: (str | None, str | None, str | None) -> APIClient
    if not registry_url:
        profile = get_profile()
        registry_url, storage_url = component_registry_url(registry_profile=profile)

    return APIClient(base_url=registry_url, storage_url=storage_url, auth_token=token)


def service_details(
        namespace=None,  # type: str | None
        service_profile=None,  # type: str | None
        config_path=None,  # type: str | None
):  # type: (...) -> ServiceDetails
    profile_name = service_profile or 'default'
    profile = get_profile(config_path, profile_name)

    if profile:
        print_info('Selected profile " {}" from the idf_component_manager.yml file'.format(profile_name))
    elif profile_name != 'default' and not profile:
        raise NoSuchProfile('"{}" didn\'t find in the idf_component_manager.yml file'.format(profile_name))

    registry_url, storage_url = component_registry_url(registry_profile=profile)

    # Priorities: CLI option > IDF_COMPONENT_NAMESPACE env variable > profile value
    namespace = get_namespace(profile, namespace)

    # Priorities: IDF_COMPONENT_API_TOKEN env variable > profile value
    token = get_token(profile)

    client = create_api_client(registry_url, storage_url, token)

    return ServiceDetails(client, namespace)
