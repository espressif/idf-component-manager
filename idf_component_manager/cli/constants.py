# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

import click

from idf_component_manager.core import ComponentManager

PROJECT_DIR_OPTION = [
    click.option(
        '--project-dir', 'manager', default=os.getcwd(), callback=lambda ctx, param, value: ComponentManager(value)),
]
SERVICE_PROFILE_OPTION = [
    click.option(
        '--service-profile',
        envvar='IDF_COMPONENT_SERVICE_PROFILE',
        default='default',
        help='Profile for component registry to use.',
    ),
]
PROJECT_OPTIONS = PROJECT_DIR_OPTION + SERVICE_PROFILE_OPTION

NAMESPACE_OPTION = [
    click.option(
        '--namespace',
        envvar='IDF_COMPONENT_NAMESPACE',
        default='espressif',
        help='Namespace for the component. Can be set in config file.',
    ),
]
NAME_OPTION = [click.option('--name', required=True, help='Component name')]
NAMESPACE_NAME_OPTIONS = NAMESPACE_OPTION + NAME_OPTION
