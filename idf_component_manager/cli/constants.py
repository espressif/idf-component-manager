# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

import click

from idf_component_manager.core import ComponentManager


def get_project_dir_option():
    PROJECT_DIR_OPTION = [
        click.option(
            '--project-dir',
            'manager',
            default=os.getcwd(),
            callback=lambda ctx, param, value: ComponentManager(value),
        ),
    ]

    return PROJECT_DIR_OPTION


def get_service_profile_option():
    SERVICE_PROFILE_OPTION = [
        click.option(
            '--service-profile',
            envvar='IDF_COMPONENT_SERVICE_PROFILE',
            default='default',
            help='Profile for component registry to use.',
        ),
    ]

    return SERVICE_PROFILE_OPTION


def get_project_options():
    PROJECT_OPTIONS = get_project_dir_option() + get_service_profile_option()
    return PROJECT_OPTIONS


def get_namespace_option():
    NAMESPACE_OPTION = [
        click.option(
            '--namespace',
            envvar='IDF_COMPONENT_NAMESPACE',
            default=None,
            help='Namespace for the component. Can be set in config file.',
        ),
    ]

    return NAMESPACE_OPTION


def get_name_option():
    NAME_OPTION = [click.option('--name', required=True, help='Component name')]

    return NAME_OPTION


def get_namespace_name_options():
    NAMESPACE_NAME_OPTIONS = get_namespace_option() + get_name_option()

    return NAMESPACE_NAME_OPTIONS


def get_dest_dir_option():
    DEST_DIR_OPTION = [
        click.option(
            '--dest-dir', default=None, help='Destination directory for the component archive.'
        )
    ]

    return DEST_DIR_OPTION
