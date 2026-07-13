# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from types import SimpleNamespace

import rich_click as click

from idf_component_manager.prepare_components.prepare import inject_requirements, prepare_dep_dirs
from idf_component_manager.root_components.install import install_root_components


@click.group(hidden=True)
def cooking():
    """Internal build-system commands."""


@cooking.command(hidden=True)
def stock():
    """Install ESP-IDF root-managed components."""
    install_root_components()


@cooking.command(hidden=True)
@click.option('--project_dir')
@click.option('--lock_path')
@click.option('--interface_version', default=4, type=int)
@click.option('--sdkconfig_json_file', required=False)
@click.option('--use_sdk_json', required=False)
@click.option('--managed_components_list_file', required=True)
@click.option('--local_components_list_file', required=False)
@click.option('--build_dir', required=False)
def prepare(**kwargs):
    """Prepare managed component directories for the build system."""
    prepare_dep_dirs(SimpleNamespace(**kwargs))


@cooking.command(hidden=True)
@click.option('--project_dir')
@click.option('--lock_path')
@click.option('--interface_version', default=4, type=int)
@click.option('--sdkconfig_json_file', required=False)
@click.option('--use_sdk_json', required=False)
@click.option('--component_requires_file', required=True)
@click.option('--build_dir', required=True)
@click.option('--idf_path', required=False)
def inject(**kwargs):
    """Inject component requirements into CMake metadata."""
    inject_requirements(SimpleNamespace(**kwargs))


def init_cooking():
    return cooking
