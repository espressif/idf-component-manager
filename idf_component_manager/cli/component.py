# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import click

from .constants import (
    get_dest_dir_option,
    get_namespace_name_options,
    get_project_dir_option,
    get_project_options,
)
from .utils import add_options


def init_component():
    PROJECT_DIR_OPTION = get_project_dir_option()
    PROJECT_OPTIONS = get_project_options()
    NAMESPACE_NAME_OPTIONS = get_namespace_name_options()
    DEST_DIR_OPTION = get_dest_dir_option()

    @click.group()
    def component():
        """
        Group of commands to interact with components.
        """
        pass

    COMPONENT_VERSION_OPTION = [
        click.option(
            '--version',
            help='Set version if not defined in the manifest. '
            'Use "git" to get version from the git tag. '
            '(command would fail if running not from a git tag)',
        )
    ]

    COMMIT_SHA_REPO_OPTION = [
        click.option(
            '--repository',
            default=None,
            help='The URL of the component repository. This option overwrites the value in the idf_component.yml',
        ),
        click.option(
            '--commit-sha',
            default=None,
            help='Git commit SHA of the the component version. This option overwrites the value in the idf_component.yml',
        ),
        click.option(
            '--repository-path',
            default=None,
            help='Path to the component in the repository. This option overwrites the value in the idf_component.yml',
        ),
    ]

    @component.command()
    @add_options(
        PROJECT_DIR_OPTION
        + NAMESPACE_NAME_OPTIONS
        + COMPONENT_VERSION_OPTION
        + DEST_DIR_OPTION
        + COMMIT_SHA_REPO_OPTION
    )
    def pack(
        manager, namespace, name, version, dest_dir, repository, commit_sha, repository_path
    ):  # noqa: namespace is not used
        """
        Create component archive and store it in the dist directory.
        """
        manager.pack_component(
            name=name,
            version=version,
            dest_dir=dest_dir,
            repository=repository,
            commit_sha=commit_sha,
            repository_path=repository_path,
        )

    @component.command()
    @add_options(
        PROJECT_OPTIONS
        + NAMESPACE_NAME_OPTIONS
        + COMPONENT_VERSION_OPTION
        + DEST_DIR_OPTION
        + COMMIT_SHA_REPO_OPTION
    )
    @click.option(
        '--archive',
        help='Path of the archive with a component to upload. '
        'When not provided the component will be packed automatically.',
    )
    @click.option(
        '--skip-pre-release',
        is_flag=True,
        default=False,
        help='Do not upload pre-release versions.',
    )
    @click.option(
        '--check-only',
        is_flag=True,
        default=False,
        help='Check if given component version is already uploaded and exit.',
    )
    @click.option(
        '--allow-existing',
        is_flag=True,
        default=False,
        help='Return success if existing version is already uploaded.',
    )
    @click.option(
        '--dry-run',
        is_flag=True,
        default=False,
        help='Upload component for validation without creating a version in the registry.',
    )
    def upload(
        manager,
        service_profile,
        namespace,
        name,
        version,
        archive,
        skip_pre_release,
        check_only,
        allow_existing,
        dry_run,
        dest_dir,
        repository,
        commit_sha,
        repository_path,
    ):
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
            dry_run=dry_run,
            dest_dir=dest_dir,
            repository=repository,
            commit_sha=commit_sha,
            repository_path=repository_path,
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
    @click.option('--version', required=True, help='Component version to delete.')
    def delete(manager, service_profile, namespace, name, version):
        """
        Delete specified version of the component from the component registry.
        The deleted version cannot be restored or re-uploaded.
        """
        manager.delete_version(name, version, service_profile=service_profile, namespace=namespace)

    @component.command()
    @add_options(PROJECT_OPTIONS + NAMESPACE_NAME_OPTIONS)
    @click.option('--version', required=True, help='Component version to yank version.')
    @click.option(
        '--message',
        required=True,
        help='Message explaining why the component version is being removed from the registry.',
    )
    def yank(manager, service_profile, namespace, name, version, message):
        """
        Yank specified version of the component from the component registry.
        Yanked version will only be downloaded if the exact version is specified in the component manifest or lock file.
        A warning message is printed every time a yanked version is downloaded.
        """
        manager.yank_version(
            name, version, message, service_profile=service_profile, namespace=namespace
        )

    return component
