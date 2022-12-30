# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import click

from .constants import NAMESPACE_NAME_OPTIONS, PROJECT_DIR_OPTION, PROJECT_OPTIONS
from .utils import add_options


@click.group()
def component():
    """
    Group of component related commands
    """
    pass


COMPONENT_VERSION_OPTION = [
    click.option(
        '--version',
        help='Set version if not defined in the manifest. Use "git" to get version from the git tag. '
        '(command would fail if running not from a git tag)',
    )
]


@component.command()
@add_options(PROJECT_DIR_OPTION + NAMESPACE_NAME_OPTIONS + COMPONENT_VERSION_OPTION)
def pack(manager, namespace, name, version):  # noqa: namespace is not used
    """
    Create component archive and store it in the dist directory.
    """
    manager.pack_component(name, version)


@component.command()
@add_options(PROJECT_OPTIONS + NAMESPACE_NAME_OPTIONS + COMPONENT_VERSION_OPTION)
@click.option(
    '--archive',
    help='Path of the archive with a component to upload. '
    'When not provided the component will be packed automatically.',
)
@click.option('--skip-pre-release', is_flag=True, default=False, help='Do not upload pre-release versions.')
@click.option(
    '--check-only', is_flag=True, default=False, help='Check if given component version is already uploaded and exit.')
@click.option(
    '--allow-existing', is_flag=True, default=False, help='Return success if existing version is already uploaded.')
def upload(manager, service_profile, namespace, name, version, archive, skip_pre_release, check_only, allow_existing):
    """
    Upload component to the component registry.

    If the component doesn't exist in the registry it will be created automatically.
    """
    manager.upload_component(
        name,
        version=version,
        service_profile=service_profile,
        namespace=namespace,
        archive=archive,
        skip_pre_release=skip_pre_release,
        check_only=check_only,
        allow_existing=allow_existing,
    )


@component.command()
@add_options(PROJECT_OPTIONS)
@click.option('--job', required=True, help='Upload job ID')
def upload_status(manager, service_profile, job):
    """
    Check the component uploading status.
    """
    manager.upload_component_status(job, service_profile=service_profile)


@component.command()
@add_options(PROJECT_OPTIONS + NAMESPACE_NAME_OPTIONS)
@click.option('--version', required=True, help='Component version to delete')
def delete(manager, service_profile, namespace, name, version):
    """
    Delete specified version of the component from the component registry.
    The deleted version cannot be restored or re-uploaded.
    """
    manager.delete_version(name, version, service_profile=service_profile, namespace=namespace)
