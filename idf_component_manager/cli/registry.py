# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import webbrowser

import click
import requests
from six.moves import input

from idf_component_manager.service_details import (
    get_profile,
    service_details_for_profile,
    validate_profile,
)
from idf_component_manager.utils import print_error, print_info
from idf_component_tools.api_client_errors import APIClientError
from idf_component_tools.config import ConfigManager
from idf_component_tools.constants import DEFAULT_NAMESPACE, IDF_COMPONENT_REGISTRY_URL
from idf_component_tools.errors import FatalError

from .constants import get_service_profile_option
from .utils import add_options


def init_registry():
    @click.group()
    def registry():
        """
        Group of commands to work with component registry
        """
        pass

    @registry.command()
    @add_options(get_service_profile_option())
    @click.option(
        '--no-browser',
        is_flag=True,
        default=False,
        help='Do not open browser and only print login URL to the terminal',
    )
    @click.option(
        '--description',
        default='Token created through CLI login',
        help='Description for the token for future reference',
    )
    @click.option(
        '--default_namespace',
        help='Default namespace to use for the components',
    )
    @click.option(
        '--registry_url',
        help='URL of the registry to use',
    )
    def login(service_profile, no_browser, description, default_namespace, registry_url):
        """
        Login to the component registry
        """

        if registry_url:
            os.environ['IDF_COMPONENT_REGISTRY_URL'] = registry_url

        # Load config for dump later
        config = ConfigManager().load()
        profile = config.profiles.setdefault(service_profile, {})

        # Check if token is already in the profile
        if 'api_token' in profile:
            raise FatalError(
                'You are already logged in with profile "{}", '
                'please either logout or use different profile'.format(service_profile)
            )

        # Get profile for API client
        api_profile = get_profile(profile_name=service_profile)
        api_profile = api_profile if api_profile else {}
        validate_profile(profile=api_profile, profile_name=service_profile, raise_on_missing=False)

        api_client, _ = service_details_for_profile(
            profile=api_profile, namespace=default_namespace, token_required=False
        )

        auth_url = '{}/tokens/'.format(api_client.frontend_url)

        auth_params = {
            'scope': 'user write:components',
            'description': description,
        }
        auth_request = requests.Request('GET', auth_url, params=auth_params).prepare()

        if no_browser:
            print_info(
                'Open this URL in your browser to login to the registry:\n\t{}'.format(
                    auth_request.url
                )
            )
        else:
            print_info(
                'If browser did not open automatically please visit this URL:\n\t{}'.format(
                    auth_request.url
                )
            )
            webbrowser.open(auth_request.url, new=2, autoraise=True)

        # Wait for token
        print_info('Please create a token in the browser window and paste here')
        token_valid = False
        while not token_valid:
            token = input('Token:')

            try:
                api_client.auth_token = token
                api_client.token_information()
                token_valid = True
            except APIClientError as e:
                # Handle 401 and 403 explicitly
                print_error(
                    'Provided token does not seem to be working: {}\nPlease try again.'.format(e)
                )
                continue

        # Update config with token and default namespace, registry URL if they are provided
        if default_namespace:
            profile['namespace'] = default_namespace
        if registry_url:
            profile['registry_url'] = registry_url
        profile['api_token'] = token

        ConfigManager().dump(config)

        print_info('Successfully logged in')

    @registry.command()
    @add_options(get_service_profile_option())
    def logout(service_profile):
        # Load config to get
        config = ConfigManager().load()

        # Check if token is already in the profile
        profile = config.profiles.setdefault(service_profile, {})
        if 'api_token' not in profile:
            raise FatalError('You are not logged in')

        del profile['api_token']
        ConfigManager().dump(config)

        print_info('Successfully logged out')

    return registry
