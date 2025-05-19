# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import click

from idf_component_manager.cli.validations import (
    validate_git_url,
    validate_if_archive,
    validate_sha,
    validate_version,
)

from .constants import (
    get_dest_dir_option,
    get_name_option,
    get_namespace_name_options,
    get_project_dir_option,
    get_project_options,
)
from .utils import add_options


def init_component():
    PROJECT_DIR_OPTION = get_project_dir_option()
    PROJECT_OPTIONS = get_project_options()
    NAME_OPTION = get_name_option()
    NAMESPACE_NAME_OPTIONS = get_namespace_name_options()
    DEST_DIR_OPTION = get_dest_dir_option()

    @click.group()
    def component():
        """
        Group of commands for interacting with components.
        """
        pass

    COMPONENT_VERSION_OPTION = [
        click.option(
            '--version',
            help='Set the version if it is not defined in the manifest. '
            'Use "git" to get the version from the Git tag. '
            '(The command will fail if not running from a Git tag.)',
        )
    ]

    COMMIT_SHA_REPO_OPTION = [
        click.option(
            '--repository',
            default=None,
            help='The URL of the component repository. This option overrides the value in the idf_component.yml file.',
            callback=validate_git_url,
        ),
        click.option(
            '--commit-sha',
            default=None,
            help='Git commit SHA of the component version. This option overrides the value in the idf_component.yml file.',
            callback=validate_sha,
        ),
        click.option(
            '--repository-path',
            default=None,
            help='Path to the component in the repository. This option overrides the value in the idf_component.yml file.',
        ),
    ]

    @component.command()
    @add_options(
        PROJECT_DIR_OPTION
        + NAME_OPTION
        + COMPONENT_VERSION_OPTION
        + DEST_DIR_OPTION
        + COMMIT_SHA_REPO_OPTION
    )
    def pack(
        manager,
        name,
        version,
        dest_dir,
        repository,
        commit_sha,
        repository_path,
    ):  # noqa: namespace is not used
        """
        Create a component archive and store it in the dist directory.
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
        help='Path to the archive of the component to upload. '
        'When not provided, the component will be packed automatically.',
        callback=validate_if_archive,
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
        help='Check if the given component version is already uploaded and exit.',
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
        help='Upload the component for validation without creating a version in the registry.',
    )
    def upload(
        manager,
        profile_name,
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
        Upload a component to the component registry.

        If the component does not exist in the registry, it will be created automatically.
        """
        manager.upload_component(
            name,
            version=version,
            profile_name=profile_name,
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
    def upload_status(manager, profile_name, job):
        """
        Check the status of a component upload.
        """
        manager.upload_component_status(job, profile_name=profile_name)

    @component.command()
    @add_options(PROJECT_OPTIONS + NAMESPACE_NAME_OPTIONS)
    @click.option(
        '--version', required=True, help='Component version to delete.', callback=validate_version
    )
    def delete(manager, profile_name, namespace, name, version):
        """
        Delete the specified version of a component from the component registry.
        The deleted version cannot be restored or re-uploaded.
        """
        manager.delete_version(name, version, profile_name=profile_name, namespace=namespace)

    @component.command()
    @add_options(PROJECT_OPTIONS + NAMESPACE_NAME_OPTIONS)
    @click.option(
        '--version',
        required=True,
        help='Component version to yank.',
        callback=validate_version,
    )
    @click.option(
        '--message',
        required=True,
        help='Message explaining why the component version is being removed from the registry.',
    )
    def yank(manager, profile_name, namespace, name, version, message):
        """
        Yank the specified version of a component from the component registry.
        A yanked version will only be downloaded if the exact version is specified in the component manifest or lock file.
        A warning message is printed every time a yanked version is downloaded.
        """
        manager.yank_version(name, version, message, profile_name=profile_name, namespace=namespace)

    return component
