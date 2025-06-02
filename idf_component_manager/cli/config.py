# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


import typing as t
from pathlib import Path

import click
from pydantic import ValidationError
from ruamel.yaml import YAML, CommentedMap

from idf_component_manager.cli.validations import validate_name
from idf_component_tools.config import ConfigError, ConfigManager, ProfileItem
from idf_component_tools.errors import FatalError
from idf_component_tools.utils import polish_validation_error


def tuple_to_list(_ctx, _param, value) -> t.List[str]:
    if value:
        return list(value)
    return value


# It is used to avoid validation of the config file while unsetting the profile or its fields
def _write_config(path: Path, data: CommentedMap, yaml: YAML) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode='w', encoding='utf-8') as f:
        yaml.dump(data, f)


def init_config():
    @click.group()
    def config():
        """
        Group of commands to edit the global configuration of the IDF Component Manager by editing "idf_component_manager.yml".
        By default, the configuration file is located in the ".espressif" directory in your home directory,
        but the path can be configured with the environment variable "IDF_TOOLS_PATH".
        """
        pass

    @config.command()
    def path():
        """
        Show path to config file.
        """
        print(ConfigManager().config_path)

    @config.command(name='list')
    def list_command():
        """
        List all profiles with tokens hidden.

        If the config file looks like this:
            profiles:
                default:
                    default_namespace: namespace
                empty_profile:
                another_profile:
                    default_namespace: another_namespace
                some_other_profile:
                    aaa: bbb
        The 'empty_profile' and 'some_other_profile' will not be printed.
        """
        config = ConfigManager().load()

        for profile_name, profile in config.profiles.items():
            if profile is not None:
                # Convert the ProfileItem to a dictionary
                profile_dict = profile.model_dump(exclude_none=False)
                # If profile does not have fields from ProfileItem, but has something else, it is not None
                if all(value is None for value in profile_dict.values()):
                    continue
                # Mask the 'api_token' field
                if profile_dict['api_token'] is not None:
                    profile_dict['api_token'] = '***hidden***'  # noqa: S105

                # Print profile details, excluding None values
                print(f'\nProfile: {profile_name}')
                for key, value in profile_dict.items():
                    if value is not None:
                        print(f'\t{key.replace("_", " ").title():<20}: {value}')

    @config.command()
    @click.option(
        '--profile',
        default='default',
        help='The name of the profile to change or add. If not provided, the default profile will be used.',
    )
    @click.option(
        '--registry-url',
        help='Set URL of the Component Registry.',
    )
    @click.option(
        '--storage-url',
        help='Set one or more storage URLs. To set a list of values, use this argument multiple times: --storage-url <url1> --storage-url <url2>',
        callback=tuple_to_list,
        multiple=True,
    )
    @click.option(
        '--local-storage-url',
        help='Set one or more local storage URLs. To set a list of values, use this argument multiple times: --local-storage-url <url1> --local-storage-url <url2>',
        callback=tuple_to_list,
        multiple=True,
    )
    @click.option('--api-token', help='Set API token.')
    @click.option(
        '--default-namespace', help='Set default namespace for components.', callback=validate_name
    )
    @click.pass_context
    def set(ctx, profile, **kwargs):
        """
        Set one or more configuration values in a profile.
        Creates the profile if it doesn't exist.
        """

        # Skip fields with None or empty lists/tuples
        set_fields = {
            k: v for k, v in ctx.params.items() if k != 'profile' and v not in (None, [], ())
        }
        if profile and not set_fields:
            raise FatalError('Please provide a parameter you want to change.')

        config_manager = ConfigManager()
        config = config_manager.load()

        if profile not in config.profiles or config.profiles[profile] is None:
            config.profiles[profile] = ProfileItem()

        try:
            for field, value in set_fields.items():
                setattr(config.profiles[profile], field, value)

            config_manager.dump(config)
        except ValidationError as e:
            raise ConfigError(f'Invalid input!\n{polish_validation_error(e)}')

        print(f"Profile '{profile}' updated with provided values.")

    @config.command()
    @click.option(
        '--profile',
        default='default',
        help='The name of the profile to change. If not provided, the default profile will be used.',
    )
    @click.option(
        '--registry-url',
        help='Remove URL of the Component Registry.',
        is_flag=True,
        default=False,
    )
    @click.option(
        '--storage-url',
        help='Remove storage URLs.',
        is_flag=True,
        default=False,
    )
    @click.option(
        '--local-storage-url',
        help='Remove local storage URLs.',
        is_flag=True,
        default=False,
    )
    @click.option('--api-token', help='Remove API token.', is_flag=True, default=False)
    @click.option(
        '--default-namespace',
        help='Remove default namespace',
        is_flag=True,
        default=False,
    )
    @click.option(
        '--all',
        is_flag=True,
        default=False,
        help='Remove the profile entirely from the config file.',
    )
    @click.pass_context
    def unset(ctx, profile, all, **kwargs):
        """
        Unset specific configuration fields or remove the entire profile from the config file.
        Use `--all` to delete the entire profile, be careful if you have unsupported/your own fields under profile.
        """

        config_manager = ConfigManager()
        config_path = config_manager.config_path
        yaml = YAML()

        # Filter out only True flags (fields to unset)
        fields_to_unset = [
            key for key, value in ctx.params.items() if key not in ('profile', 'all') and value
        ]

        if not fields_to_unset and not all:
            raise FatalError(
                'Please provide at least one field to unset or use --all to remove the profile.'
            )

        # Load raw data
        try:
            raw_data = config_manager.data
        except ConfigError as e:
            raise FatalError(str(e))

        if 'profiles' not in raw_data:
            raw_data['profiles'] = CommentedMap()

        if profile not in raw_data['profiles']:
            raise ConfigError(f"Profile '{profile}' does not exist.")

        if all:
            del raw_data['profiles'][profile]
            _write_config(config_path, raw_data, yaml)
            print(f'Profile "{profile}" was completely removed from the config file.')
            return

        # Track which fields were actually removed
        removed_fields = []
        for field in fields_to_unset:
            # Fix: Check if field exists before trying to delete it
            if field in raw_data['profiles'][profile]:
                del raw_data['profiles'][profile][field]
                removed_fields.append(field)

        # Warn if no fields were actually removed
        if not removed_fields:
            print(f'No specified fields found in profile "{profile}".')
            return

        # Remove the profile if it becomes empty
        if not raw_data['profiles'][profile]:
            del raw_data['profiles'][profile]

        _write_config(config_path, raw_data, yaml)

        print(f'Successfully removed {", ".join(removed_fields)} from the profile "{profile}".')

    return config
