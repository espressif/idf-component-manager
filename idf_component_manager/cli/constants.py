# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import typing as t

import click

from idf_component_manager.core import ComponentManager
from idf_component_manager.utils import validate_name


def get_project_dir_option() -> t.List[click.Option]:
    return [
        click.option(
            '--project-dir',
            'manager',
            default=os.getcwd(),
            callback=lambda ctx, param, value: ComponentManager(value),
        ),
    ]


def get_profile_option() -> t.List[click.Option]:
    return [
        click.option(
            '--profile',
            '--service-profile',
            'profile_name',
            envvar='IDF_COMPONENT_PROFILE',
            default='default',
            help=(
                'Specifies the profile to use for this command. '
                'Alias "--service-profile" is deprecated and will be removed.'
            ),
        ),
    ]


def get_project_options() -> t.List[click.Option]:
    return get_project_dir_option() + get_profile_option()


def get_namespace_option() -> t.List[click.Option]:
    return [
        click.option(
            '--namespace',
            envvar='IDF_COMPONENT_NAMESPACE',
            default=None,
            help='Namespace for the component. Can be set in config file.',
        ),
    ]


def get_name_option() -> t.List[click.Option]:
    return [click.option('--name', required=True, callback=validate_name, help='Component name')]


def get_namespace_name_options() -> t.List[click.Option]:
    NAMESPACE_NAME_OPTIONS = get_namespace_option() + get_name_option()

    return NAMESPACE_NAME_OPTIONS


def get_dest_dir_option() -> t.List[click.Option]:
    return [
        click.option(
            '--dest-dir',
            default=None,
            help='Destination directory for the component archive.',
        )
    ]
