# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t
import webbrowser
from urllib.parse import urljoin

import click
import requests

from idf_component_manager.cli.validations import (
    combined_callback,
    validate_name,
    validate_registry_component,
    validate_url,
)
from idf_component_manager.core import ComponentManager
from idf_component_manager.utils import VersionSolverResolution
from idf_component_tools import warn
from idf_component_tools.config import ConfigManager, ProfileItem, get_profile
from idf_component_tools.errors import FatalError
from idf_component_tools.registry.client_errors import APIClientError
from idf_component_tools.registry.service_details import get_api_client

from .constants import get_profile_option, get_project_dir_option
from .utils import add_options, deprecated_option


def init_registry():
    @click.group()
    def registry():
        """
        Group of commands to work with the component registry.
        """
        pass

    @registry.command()
    @add_options(get_profile_option())
    @click.option(
        '--no-browser',
        is_flag=True,
        default=False,
        help='Do not open the browser; only print the login URL to the terminal.',
    )
    @click.option(
        '--description',
        default='Token created through CLI login.',
        help='Description of the token for future reference.',
    )
    @click.option(
        '--default-namespace',
        help='Default namespace to use for components.',
        callback=validate_name,
    )
    @click.option(
        '--default_namespace',
        help="This argument has been deprecated by '--default-namespace'.",
        hidden=True,
        callback=combined_callback(deprecated_option, validate_name),
        expose_value=False,
    )
    @click.option(
        '--registry-url',
        help='URL of the registry to use.',
        callback=validate_url,
    )
    @click.option(
        '--registry_url',
        help="This argument has been deprecated by '--registry-url'.",
        hidden=True,
        callback=combined_callback(deprecated_option, validate_url),
        expose_value=False,
    )
    def login(profile_name, no_browser, description, default_namespace, registry_url):
        """
        Login to the component registry.
        """
        # Load config for dump later
        config = ConfigManager().load()
        if profile_name not in config.profiles:
            profile = ProfileItem()
            config.profiles[profile_name] = profile
        else:
            profile = config.profiles[profile_name]

        # Check if token is already in the profile
        if profile.api_token:
            raise FatalError(
                f'You are already logged in with profile "{profile_name}", '
                'please either logout or use a different profile'
            )

        api_client = get_api_client(
            registry_url,
            namespace=default_namespace,
            profile_name=profile_name,
            profile=profile,
        )

        auth_url = urljoin(api_client.registry_url, 'settings/tokens')

        auth_params = {
            'scope': 'user write:components',
            'description': description,
        }
        auth_request = requests.Request('GET', auth_url, params=auth_params).prepare()

        if no_browser:
            print(f'Open this URL in your browser to login to the registry:\n\t{auth_request.url}')
        else:
            print(
                f'If browser did not open automatically please visit this URL:\n\t{auth_request.url}'
            )
            webbrowser.open(auth_request.url, new=2, autoraise=True)

        # Wait for token
        print('Please create a token in the browser window and paste here')
        token_valid = False
        while not token_valid:
            token = input('Token:')

            try:
                api_client.api_token = token
                api_client.token_information()
                token_valid = True
            except APIClientError as e:
                # Handle 401 and 403 explicitly
                print(f'ERROR: Provided token does not seem to be working: {e}\nPlease try again.')
                continue

        # Update config with token and default namespace, registry URL if they are provided
        if default_namespace:
            profile.default_namespace = default_namespace
        if registry_url:
            profile.registry_url = registry_url
        profile.api_token = token

        ConfigManager().dump(config)

        print('Successfully logged in')

    @registry.command()
    @add_options(get_profile_option())
    @click.option(
        '--no-revoke',
        is_flag=True,
        default=False,
        help='Do not revoke the token on the server side when logging out.',
    )
    def logout(profile_name, no_revoke):
        """
        Log out from the component registry.
        Removes the token from the profile and revokes it on the registry.
        """

        # Load config to get
        config = ConfigManager().load()

        # Check if token is already in the profile
        profile = get_profile(profile_name)
        if profile.api_token is None:
            raise FatalError('You are not logged in')

        if not no_revoke:
            api_client = get_api_client(profile=profile)
            try:
                api_client.revoke_current_token()
            except APIClientError:
                warn('Failed to revoke token from the registry. Probably it was revoked before.')

        profile.api_token = None
        ConfigManager().dump(config)

        print('Successfully logged out')

    @registry.command()
    @add_options(get_profile_option() + get_project_dir_option())
    @click.option(
        '--interval',
        default=0,
        help='Set the frequency (in seconds) for component synchronization. '
        'If set to 0, the program will run once and then terminate.',
    )
    @click.option(
        '--recursive',
        '-R',
        is_flag=True,
        default=False,
        help='Search for components recursively',
    )
    @click.option(
        '--component',
        multiple=True,
        default=[],
        help='Specify the components to sync from the registry. '
        'Use multiple --component options for multiple components. '
        'Format: namespace/name<version_spec>. Example: example/cmp==1.0.0',
        callback=validate_registry_component,
    )
    @click.option(
        '--resolution',
        type=click.Choice([r.value for r in VersionSolverResolution]),
        default=VersionSolverResolution.ALL.value,
        help='Resolution strategy for syncing components. By default, all versions are synced. '
        'If set to "latest", only the latest version of each component will be synced.',
    )
    @click.argument('path', required=True)
    def sync(
        manager: ComponentManager,
        profile_name: str,
        interval: int,
        component: t.List[str],
        recursive: bool,
        resolution: VersionSolverResolution,
        path: str,
    ) -> None:
        """
        Sync components from the registry to a local directory.
        """
        manager.sync_registry(
            profile_name,
            path,
            interval=interval,
            components=component,
            recursive=recursive,
            resolution=resolution,
        )

    return registry
