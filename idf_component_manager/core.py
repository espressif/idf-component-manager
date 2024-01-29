# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Core module of component manager"""
from __future__ import print_function

import functools
import os
import re
import shutil
import tarfile
import tempfile
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from io import open
from pathlib import Path

import requests
from requests_toolbelt import MultipartEncoderMonitor

from idf_component_manager.utils import ComponentSource, print_info, print_warn
from idf_component_tools.archive_tools import pack_archive, unpack_archive
from idf_component_tools.build_system_tools import build_name, is_component
from idf_component_tools.config import root_managed_components_dir
from idf_component_tools.environment import getenv_int
from idf_component_tools.errors import (
    FatalError,
    GitError,
    InternalError,
    ManifestError,
    NothingToDoError,
    VersionAlreadyExistsError,
    VersionNotFoundError,
)
from idf_component_tools.file_tools import (
    check_unexpected_component_files,
    copy_filtered_directory,
    create_directory,
)
from idf_component_tools.git_client import GitClient
from idf_component_tools.hash_tools.errors import (
    HashDoesNotExistError,
    HashNotEqualError,
    HashNotSHA256Error,
)
from idf_component_tools.hash_tools.validate_managed_component import (
    validate_managed_component_hash,
)
from idf_component_tools.manifest import (
    MANIFEST_FILENAME,
    WEB_DEPENDENCY_REGEX,
    Manifest,
    ManifestManager,
    ProjectRequirements,
)
from idf_component_tools.registry.api_client_errors import (
    APIClientError,
    ComponentNotFound,
    NetworkConnectionError,
    VersionNotFound,
)
from idf_component_tools.semver import SimpleSpec, Version
from idf_component_tools.sources import WebServiceSource
from idf_component_tools.utils import lru_cache

from .cmake_component_requirements import (
    CMakeRequirementsManager,
    ComponentName,
    RequirementsProcessingError,
    check_requirements_name_collisions,
    handle_project_requirements,
)
from .core_utils import (
    ProgressBar,
    archive_filename,
    copy_examples_folders,
    dist_name,
    parse_example,
    raise_component_modified_error,
)
from .dependencies import download_project_dependencies
from .local_component_list import parse_component_list
from .service_details import get_api_client, get_storage_client

try:
    from typing import Optional, Tuple
except ImportError:
    pass


# PROCESSING_TIMEOUT
def get_processing_timeout():
    try:
        return getenv_int('COMPONENT_MANAGER_JOB_TIMEOUT', 300)
    except ValueError:
        print_warn(
            'Cannot parse value of COMPONENT_MANAGER_JOB_TIMEOUT.'
            ' It should be number of seconds to wait for job result.'
        )
        return 300


CHECK_INTERVAL = 3
MAX_PROGRESS = 100  # Expected progress is in percent


def general_error_handler(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except NetworkConnectionError as e:
            raise FatalError(
                '\n'.join(
                    [
                        'Cannot establish a connection to the component registry. '
                        'Are you connected to the internet?',
                    ]
                    + e.request_info()
                )
            )

        except APIClientError as e:
            raise FatalError('\n'.join([str(e)] + e.request_info()))

    return wrapper


def _create_manifest_if_missing(manifest_dir):  # type: (str) -> bool
    manifest_filepath = os.path.join(manifest_dir, MANIFEST_FILENAME)
    if os.path.exists(manifest_filepath):
        return False
    example_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), 'templates', 'idf_component_template.yml'
    )
    create_directory(manifest_dir)
    shutil.copyfile(example_path, manifest_filepath)
    print_info('Created "{}"'.format(manifest_filepath))
    return True


class ComponentManager(object):
    def __init__(self, path, lock_path=None, manifest_path=None, interface_version=0):
        # type: (str, Optional[str], Optional[str], int) -> None

        # Working directory
        path = os.path.abspath(path)
        self.path = path

        # Set path of the project's main component
        self.main_component_path = os.path.join(path, 'main')

        # Set path of the manifest file for the project's main component
        self.main_manifest_path = manifest_path or (
            os.path.join(path, 'main', MANIFEST_FILENAME) if os.path.isdir(path) else path
        )
        self.main_component_path = os.path.normpath(self.main_component_path)

        # Lock path
        if not lock_path:
            if os.path.isfile(path):
                self.lock_path = path
            else:
                self.lock_path = os.path.join(path, 'dependencies.lock')
        elif os.path.isabs(lock_path):
            self.lock_path = lock_path
        else:
            self.lock_path = os.path.join(path, lock_path)

        self.lock_path = os.path.abspath(self.lock_path)

        # Components directories
        self.components_path = os.path.join(self.path, 'components')
        self.managed_components_path = os.path.join(self.path, 'managed_components')

        # Dist directory
        self.dist_path = os.path.join(self.path, 'dist')

        self.interface_version = interface_version

    def _get_manifest_dir(self, component='main', path=None):  # type: (str, Optional[str]) -> str
        if component != 'main' and path is not None:
            raise FatalError(
                'Cannot determine manifest directory. Please specify either component or path.'
            )

        # If path is specified
        if path is not None:
            manifest_dir = os.path.abspath(path)
        # If the current working directory is in the context of a component
        elif is_component(Path(os.getcwd())):
            manifest_dir = os.getcwd()
        else:
            # If the current working directory is in the context of a project
            base_dir = self.path if component == 'main' else self.components_path
            manifest_dir = os.path.join(base_dir, component)

        if not os.path.isdir(manifest_dir):
            raise FatalError(
                'Directory "{}" does not exist! '
                'Please specify a valid component under {} or try to use --path'.format(
                    manifest_dir, self.path
                )
            )
        if not manifest_dir.startswith(self.path):
            raise FatalError(
                'Directory "{}" is not under project directory! '
                'Please specify a valid component under {}'.format(manifest_dir, self.path)
            )

        return manifest_dir

    @property
    @lru_cache(1)
    def root_managed_components_dir(self):  # type: () -> str
        return root_managed_components_dir()  # type: ignore

    @property
    @lru_cache(1)
    def root_managed_components_lock_path(self):  # type: () -> str
        return os.path.join(self.root_managed_components_dir, 'dependencies.lock')  # type: ignore

    def _get_manifest(
        self, component='main', path=None
    ):  # type: (str, Optional[str]) -> Tuple[str, bool]
        manifest_dir = self._get_manifest_dir(component=component, path=path)
        manifest_filepath = os.path.join(manifest_dir, MANIFEST_FILENAME)
        # Create manifest file if it doesn't exist in work directory
        manifest_created = _create_manifest_if_missing(manifest_dir)
        return manifest_filepath, manifest_created

    @general_error_handler
    def create_manifest(self, component='main', path=None):  # type: (str, Optional[str]) -> None
        manifest_filepath, created = self._get_manifest(component=component, path=path)
        if not created:
            print_info('"{}" already exists, skipping...'.format(manifest_filepath))

    @general_error_handler
    def create_project_from_example(self, example, path=None, service_profile=None):
        # type: (str, str | None, str | None) -> None
        client, namespace = get_storage_client(None, service_profile)
        component_name, version_spec, example_name = parse_example(example, namespace)
        project_path = path or os.path.join(self.path, os.path.basename(example_name))

        if os.path.isfile(project_path):
            raise FatalError(
                'Your target path is not a directory. '
                'Please remove the {} or use different target path.'.format(
                    os.path.abspath(project_path)
                ),
                exit_code=4,
            )

        if os.path.isdir(project_path) and os.listdir(project_path):
            raise FatalError(
                'The directory {} is not empty. '
                'To create an example you must empty the directory or '
                'choose a different path.'.format(project_path),
                exit_code=3,
            )

        component_details = client.component(component_name=component_name, version=version_spec)

        try:
            example_url = [
                example for example in component_details.examples if example_name == example['name']
            ][-1]
        except IndexError:
            raise FatalError(
                'Cannot find example "{}" for "{}" version "{}"'.format(
                    example_name, component_name, version_spec
                ),
                exit_code=2,
            )

        response = requests.get(example_url['url'], stream=True)
        with tarfile.open(fileobj=response.raw, mode='r|gz') as tar:
            tar.extractall(project_path)
        print_info(
            'Example "{}" successfully downloaded to {}'.format(
                example_name, os.path.abspath(project_path)
            )
        )

    @general_error_handler
    def add_dependency(
        self, dependency, component='main', path=None, service_profile=None
    ):  # type: (str, str, Optional[str], str | None) -> None
        manifest_filepath, _ = self._get_manifest(component=component, path=path)
        client, _ = get_storage_client(None, service_profile)

        if path is not None:
            component_path = os.path.abspath(path)
            component = os.path.basename(component_path)
        # If the path refers to a component context
        # we need to use the components name as the component
        elif is_component(Path(os.getcwd())):
            component = os.path.basename(os.path.normpath(self.path))

        match = re.match(WEB_DEPENDENCY_REGEX, dependency)
        if match:
            name, spec = match.groups()
        else:
            raise FatalError(
                'Invalid dependency: "{}". Please use format "namespace/name".'.format(dependency)
            )

        if not spec:
            spec = '*'

        try:
            SimpleSpec(spec)
        except ValueError:
            raise FatalError(
                'Invalid dependency version requirement: {}. '
                'Please use format like ">=1" or "*".'.format(spec)
            )

        name = WebServiceSource().normalized_name(name)

        # Check if dependency exists in the registry
        client.component(component_name=name, version=spec)

        manifest_manager = ManifestManager(manifest_filepath, component)
        manifest = manifest_manager.load()

        for dep in manifest.raw_dependencies:
            if dep.name == name:
                raise FatalError(
                    'Dependency "{}" already exists for in manifest "{}"'.format(
                        name, manifest_filepath
                    )
                )

        with open(manifest_filepath, 'r', encoding='utf-8') as file:
            file_lines = file.readlines()

        index = 0
        if 'dependencies' in manifest_manager.manifest_tree.keys():
            for i, line in enumerate(file_lines):
                if line.startswith('dependencies:'):
                    index = i + 1
                    break
        else:
            file_lines.append('\ndependencies:\n')
            index = len(file_lines) + 1

        file_lines.insert(index, '  {}: "{}"\n'.format(name, spec))

        # Check result for correctness
        with tempfile.NamedTemporaryFile(delete=False) as temp_manifest_file:
            temp_manifest_file.writelines(line.encode('utf-8') for line in file_lines)

        try:
            ManifestManager(temp_manifest_file.name, name).load()
        except ManifestError:
            raise ManifestError(
                'Cannot update manifest file. '
                "It's likely due to the 4 spaces used for "
                'indentation we recommend using 2 spaces indent. '
                'Please check the manifest file:\n{}'.format(manifest_filepath)
            )

        shutil.move(temp_manifest_file.name, manifest_filepath)
        print_info(
            'Successfully added dependency "{}{}" to component "{}"'.format(
                name, spec, manifest_manager.name
            )
        )

    @general_error_handler
    def pack_component(
        self, name, version, dest_dir=None, repository=None, commit_sha=None, repository_path=None
    ):  # type: (str, str, str | None, str | None, str | None, str | None) -> tuple[str, Manifest]
        dest_path = os.path.join(self.path, dest_dir) if dest_dir else self.dist_path

        if version == 'git':
            try:
                version = str(GitClient().get_tag_version())
            except GitError:
                raise FatalError('An error happened while getting version from git tag')
        elif version:
            try:
                Version.parse(version)
            except ValueError:
                raise FatalError(
                    'Version parameter must be either "git" or a valid version. '
                    'Documentation: https://docs.espressif.com/projects/idf-component-manager/en/latest/reference/versioning.html#versioning-scheme'
                )

        manifest_manager = ManifestManager(
            self.path,
            name,
            check_required_fields=True,
            version=version,
            repository=repository,
            commit_sha=commit_sha,
            repository_path=repository_path,
        )
        manifest = manifest_manager.load()
        dest_temp_dir = Path(dest_path, dist_name(manifest))
        include = set(manifest.files['include'])
        exclude = set(manifest.files['exclude'])
        copy_filtered_directory(self.path, str(dest_temp_dir), include=include, exclude=exclude)

        if manifest.examples:
            copy_examples_folders(
                manifest.examples, Path(self.path), dest_temp_dir, include=include, exclude=exclude
            )

        manifest_manager.dump(str(dest_temp_dir))

        check_unexpected_component_files(str(dest_temp_dir))

        archive_filepath = os.path.join(dest_path, archive_filename(manifest))
        print_info('Saving archive to "{}"'.format(archive_filepath))
        pack_archive(str(dest_temp_dir), archive_filepath)
        return archive_filepath, manifest

    @general_error_handler
    def delete_version(
        self,
        name,  # type: str
        version,  # type: str
        service_profile=None,  # type: str | None
        namespace=None,  # type: str | None
    ):  # type: (...) -> None
        client, namespace = get_api_client(namespace, service_profile)
        if not version:
            raise FatalError('Argument "version" is required')

        component_name = '/'.join([namespace, name])
        # Checking if current version already uploaded
        versions = client.versions(component_name=component_name).versions

        if version not in versions:
            raise VersionNotFoundError(
                'Version {} of the component "{}" is not on the registry'.format(
                    version, component_name
                )
            )

        client.delete_version(component_name=component_name, component_version=version)
        print_info('Deleted version {} of the component {}'.format(component_name, version))

    @general_error_handler
    def yank_version(
        self,
        name,  # type: str
        version,  # type: str
        message,  # type: str
        service_profile=None,  # type: str | None
        namespace=None,  # type: str | None
    ):
        client, namespace = get_api_client(namespace, service_profile)
        component_name = '/'.join([namespace, name])

        versions = client.versions(component_name=component_name).versions

        if version not in versions:
            raise VersionNotFoundError(
                'Version {} of the component "{}" is not on the registry'.format(
                    version, component_name
                )
            )

        client.yank_version(
            component_name=component_name, component_version=version, yank_message=message
        )
        print_info(
            'Version {} of the component {} was yanked due to reason "{}"'.format(
                component_name, version, message
            )
        )

    @general_error_handler
    def remove_managed_components(
        self, **kwargs
    ):  # kwargs here to keep idf_extension.py compatibility
        managed_components_dir = Path(self.path, 'managed_components')

        if not managed_components_dir.is_dir():
            return

        undeleted_components = []
        for component_dir in managed_components_dir.glob('*/'):
            if not (managed_components_dir / component_dir).is_dir():
                continue

            try:
                validate_managed_component_hash(str(managed_components_dir / component_dir))
                shutil.rmtree(str(managed_components_dir / component_dir))
            except (HashNotEqualError, HashNotSHA256Error):
                undeleted_components.append(component_dir.name)
            except HashDoesNotExistError:
                pass

        if undeleted_components:
            raise_component_modified_error(str(managed_components_dir), undeleted_components)

        elif any(managed_components_dir.iterdir()) == 0:
            shutil.rmtree(str(managed_components_dir))

    @general_error_handler
    def upload_component(
        self,
        name,  # type: str
        version=None,  # type: str | None
        service_profile=None,  # type: str | None
        namespace=None,  # type: str | None
        archive=None,  # type: str | None
        skip_pre_release=False,  # type: bool
        check_only=False,  # type: bool
        allow_existing=False,  # type: bool
        dry_run=False,  # type: bool
        dest_dir=None,  # type: str | None
        repository=None,  # type: str | None
        commit_sha=None,  # type: str | None
        repository_path=None,  # type: str | None
    ):  # type: (...) -> None
        """
        Uploads a component version to the registry.
        """
        token_required = not (check_only or dry_run)
        client, namespace = get_api_client(
            namespace, service_profile, token_required=token_required
        )

        if archive:
            if not os.path.isfile(archive):
                raise FatalError('Cannot find archive to upload: {}'.format(archive))

            if version:
                raise FatalError(
                    'Parameters "version" and "archive" are not supported at the same time'
                )

            tempdir = tempfile.mkdtemp()
            try:
                unpack_archive(archive, tempdir)
                manifest = ManifestManager(tempdir, name, check_required_fields=True).load()
            finally:
                shutil.rmtree(tempdir)
        else:
            archive, manifest = self.pack_component(
                name=name,
                version=version,
                dest_dir=dest_dir,
                repository=repository,
                commit_sha=commit_sha,
                repository_path=repository_path,
            )

        if not manifest.version:
            raise FatalError('"version" field is required when uploading the component')

        if not manifest.version.is_semver:
            raise FatalError('Only components with semantic versions are allowed on the service')

        if manifest.version.semver.prerelease and skip_pre_release:
            raise NothingToDoError('Skipping pre-release version {}'.format(manifest.version))

        component_name = '/'.join([namespace, manifest.name])
        # Checking if current version already uploaded
        try:
            versions = client.versions(component_name=component_name, spec='*').versions

            if manifest.version in versions:
                if allow_existing:
                    return

                raise VersionAlreadyExistsError(
                    'Version {} of the component "{}" is already on the registry'.format(
                        manifest.version, component_name
                    )
                )
        except (ComponentNotFound, VersionNotFound):
            # It's ok if component doesn't exist yet
            pass

        # Exit if check flag was set
        if check_only:
            return

        # Uploading/validating the component
        info_message = 'Uploading' if not dry_run else 'Validating'
        print_info('{} archive {}'.format(info_message, archive))

        file_stat = os.stat(archive)  # type: ignore
        with ProgressBar(
            total=file_stat.st_size, unit='B', unit_scale=True, leave=False
        ) as progress_bar:
            memo = {'progress': 0}

            def callback(monitor):  # type: (MultipartEncoderMonitor) -> None
                progress_bar.update(monitor.bytes_read - memo['progress'])
                memo['progress'] = monitor.bytes_read

            if dry_run:
                job_id = client.validate_version(file_path=archive, callback=callback)
            else:
                job_id = client.upload_version(
                    component_name=component_name, file_path=archive, callback=callback
                )

            progress_bar.close()

        # Wait for processing
        profile_text = (
            ''
            if service_profile is None or service_profile == 'default'
            else ' --service-profile={}'.format(service_profile)
        )
        print_info(
            'Wait for processing, it is safe to press CTRL+C and exit\n'
            'You can check the state of processing by running CLI command '
            '"compote component upload-status --job={} {}"'.format(job_id, profile_text)
        )

        timeout_at = datetime.now() + timedelta(seconds=get_processing_timeout())

        try:
            warnings = set()
            with ProgressBar(total=MAX_PROGRESS, unit='%', leave=False) as progress_bar:
                while True:
                    if datetime.now() > timeout_at:
                        raise TimeoutError()
                    status = client.task_status(job_id=job_id)

                    for warning in status.warnings:
                        if warning not in warnings:
                            warnings.add(warning)

                    if status.status == 'failure' or status.status == 'success':
                        progress_bar.close()
                        for warning in warnings:
                            print_warn(warning)

                    if status.status == 'failure':
                        if dry_run:
                            raise FatalError(
                                'Uploaded component did not pass validation successfully.\n%s'
                                % status.message
                            )
                        else:
                            raise FatalError(
                                "Uploaded component wasn't processed successfully.\n%s"
                                % status.message
                            )
                    elif status.status == 'success':
                        print_info(status.message)
                        return

                    progress_bar.set_description(status.message)
                    progress_bar.update_to(status.progress)

                    time.sleep(CHECK_INTERVAL)
        except TimeoutError:
            raise FatalError(
                "Component wasn't processed in {} seconds. Check processing status later.".format(
                    get_processing_timeout()
                )
            )

    @general_error_handler
    def upload_component_status(
        self, job_id, service_profile=None
    ):  # type: (str, str | None) -> None
        client, _ = get_api_client(None, service_profile)
        status = client.task_status(job_id=job_id)
        if status.status == 'failure':
            raise FatalError("Uploaded version wasn't processed successfully.\n%s" % status.message)
        else:
            print_info('Status: %s. %s' % (status.status, status.message))

    def update_dependencies(self, **kwargs):
        if os.path.isfile(self.lock_path):
            os.remove(self.lock_path)

    ## Function executed from CMake

    @general_error_handler
    def prepare_dep_dirs(
        self, managed_components_list_file, component_list_file, local_components_list_file=None
    ):
        """Process all manifests and download all dependencies"""
        # root core components
        root_manifest_filepath = os.path.join(root_managed_components_dir(), MANIFEST_FILENAME)
        if os.path.isfile(root_manifest_filepath):
            root_managed_components = download_project_dependencies(
                ProjectRequirements(
                    [
                        ManifestManager(
                            self.root_managed_components_dir,
                            'root',
                            expand_environment=True,
                            process_opt_deps=True,
                        ).load()
                    ]
                ),
                self.root_managed_components_lock_path,
                self.root_managed_components_dir,
                is_idf_root_dependencies=True,
            )
        else:
            root_managed_components = []

        # Find all components
        local_components = []
        if local_components_list_file and os.path.isfile(local_components_list_file):
            local_components = parse_component_list(local_components_list_file)
        else:
            local_components.append({'name': 'main', 'path': self.main_component_path})

            if os.path.isdir(self.components_path):
                local_components.extend(
                    {'name': item, 'path': os.path.join(self.components_path, item)}
                    for item in os.listdir(self.components_path)
                    if os.path.isdir(os.path.join(self.components_path, item))
                )

        # Check that CMakeLists.txt and idf_component.yml exists for all component dirs
        local_components = [
            component
            for component in local_components
            if os.path.isfile(os.path.join(component['path'], 'CMakeLists.txt'))
            and os.path.isfile(os.path.join(component['path'], MANIFEST_FILENAME))
        ]

        downloaded_components = set()
        if local_components:
            manifests = []

            for component in local_components:
                manifests.append(
                    ManifestManager(
                        component['path'],
                        component['name'],
                        expand_environment=True,
                        process_opt_deps=True,
                    ).load()
                )

            project_requirements = ProjectRequirements(manifests)
            downloaded_components = download_project_dependencies(
                project_requirements, self.lock_path, self.managed_components_path
            )

        # Exclude requirements paths
        downloaded_components = {
            comp
            for comp in downloaded_components
            if comp.downloaded_path not in [local_comp['path'] for local_comp in local_components]
        }

        # Include managed components in project directory
        all_managed_components = set(
            sorted(downloaded_components) + sorted(root_managed_components)
        )
        with open(managed_components_list_file, mode='w', encoding='utf-8') as file:
            for is_root, group in enumerate([downloaded_components, root_managed_components]):
                for downloaded_component in group:
                    file.write(
                        u'idf_build_component("{}" "{}")\n'.format(
                            downloaded_component.abs_posix_path,
                            'idf_components' if is_root == 1 else 'project_managed_components',
                        )
                    )
                    file.write(
                        u'idf_component_set_property({} {} "{}")\n'.format(
                            downloaded_component.name,
                            'COMPONENT_VERSION',
                            downloaded_component.version,
                        )
                    )

                    if downloaded_component.targets:
                        file.write(
                            u'idf_component_set_property({} {} "{}")\n'.format(
                                downloaded_component.name,
                                'REQUIRED_IDF_TARGETS',
                                ' '.join(downloaded_component.targets),
                            )
                        )

            file.write(
                u'set(managed_components "%s")\n'
                % ';'.join(component.name for component in all_managed_components)
            )

        # Saving list of all components with manifests for use on requirements injection step
        all_components = sorted(
            set(component.abs_path for component in all_managed_components).union(
                component['path'] for component in local_components
            )
        )
        with open(component_list_file, mode='w', encoding='utf-8') as file:
            file.write(u'\n'.join(all_components))

    @general_error_handler
    def inject_requirements(
        self,
        component_requires_file,  # type: Path | str
        component_list_file,  # type: Path | str
    ):
        '''Set build dependencies for components with manifests'''
        requirements_manager = CMakeRequirementsManager(component_requires_file)
        requirements = requirements_manager.load()

        try:
            with open(component_list_file, mode='r', encoding='utf-8') as f:
                components_with_manifests = f.readlines()
            os.remove(component_list_file)
        except FileNotFoundError:
            raise FatalError(
                'Cannot find component list file. '
                'Please make sure this script is executed from CMake'
            )

        add_all_components_to_main = False
        for component in components_with_manifests:
            component = component.strip()
            name = os.path.basename(component)
            manifest = ManifestManager(
                component, name, expand_environment=True, process_opt_deps=True
            ).load()
            name_key = ComponentName('idf', name)

            for dependency in manifest.dependencies:
                # Meta dependencies, like 'idf' are not used directly
                if dependency.meta:
                    continue

                # No required dependencies shouldn't be added to the build system
                if not dependency.require:
                    continue

                dependency_name = build_name(dependency.name)
                requirement_key = 'REQUIRES' if dependency.public else 'PRIV_REQUIRES'

                def add_req(key):  # type: (str) -> None
                    if key not in requirements[name_key]:
                        requirements[name_key][key] = []

                    req = requirements[name_key][key]
                    if isinstance(req, list) and dependency_name not in req:
                        req.append(dependency_name)

                add_req(requirement_key)

                managed_requirement_key = 'MANAGED_{}'.format(requirement_key)
                add_req(managed_requirement_key)

                # In interface v0, component_requires_file contains also common requirements
                if self.interface_version == 0 and name_key == ComponentName('idf', 'main'):
                    add_all_components_to_main = True

        # If there are dependencies added to the `main` component,
        # and common components were included to the requirements file
        # then add every other component to it dependencies
        # to reproduce convenience behavior
        # for the standard project defined in IDF's `project.cmake`
        # For ESP-IDF < 5.0 (Remove after ESP-IDF 4.4 EOL)
        if add_all_components_to_main:
            main_reqs = requirements[ComponentName('idf', 'main')]['REQUIRES']
            for requirement in requirements.keys():
                name = requirement.name
                if name not in main_reqs and name != 'main' and isinstance(main_reqs, list):
                    main_reqs.append(name)

        if self.interface_version >= 3:
            new_requirements = self._override_requirements_by_component_sources(requirements)
        else:
            new_requirements = requirements
            # we still use this function to check name collisions before 5.2
            # The behavior is different when
            #   two components with the same name but have different namespaces
            # before IDF interface 3, we consider them acceptable, and choose the first one
            # after IDF interface 3, we raise an requirement conflict error
            #   if they are under the same component type
            check_requirements_name_collisions(new_requirements)

        handle_project_requirements(new_requirements)
        requirements_manager.dump(new_requirements)

    @staticmethod
    def _override_requirements_by_component_sources(
        requirements,  # type: OrderedDict[ComponentName, dict[str, list[str] | str]]
    ):  # type: (...) -> OrderedDict[ComponentName, dict[str, list[str] | str]]
        """
        group the requirements, the overriding sequence here is: (the latter, the higher priority)
        - idf_components (IDF_PATH/components)
        - idf_managed_components (IDF_TOOLS_DIR/root_managed_components/idf5.3/managed_components)
        - project_managed_components (project_managed_components)
        - project_extra_components (project_extra_components)
        - project_components (PROJECT_DIR/components)

        idf_managed_components is injected together with `project_managed_components`
        in the `prepare_dep_dirs` step
        """
        idf_components = OrderedDict()
        project_managed_components = OrderedDict()
        project_extra_components = OrderedDict()
        project_components = OrderedDict()
        for comp_name, props in requirements.items():
            if props['__COMPONENT_SOURCE'] == ComponentSource.IDF_COMPONENTS:
                idf_components[comp_name] = props
            elif props['__COMPONENT_SOURCE'] == ComponentSource.PROJECT_MANAGED_COMPONENTS:
                project_managed_components[comp_name] = props
            elif props['__COMPONENT_SOURCE'] == ComponentSource.PROJECT_EXTRA_COMPONENTS:
                project_extra_components[comp_name] = props
            elif props['__COMPONENT_SOURCE'] == ComponentSource.PROJECT_COMPONENTS:
                project_components[comp_name] = props
            else:
                raise InternalError

        # overriding the sequence
        new_requirements = project_components
        for component_group in [
            project_extra_components,
            project_managed_components,
            idf_components,
        ]:
            for comp_name, props in component_group.items():
                name_matched_before = None
                if comp_name in new_requirements:
                    name_matched_before = comp_name
                else:
                    comp_name_without_namespace = ComponentName(
                        comp_name.prefix, comp_name.name_without_namespace
                    )
                    if comp_name_without_namespace in new_requirements:
                        name_matched_before = comp_name_without_namespace
                    else:
                        for _req_name, _req_props in new_requirements.items():
                            if comp_name_without_namespace == ComponentName(
                                _req_name.prefix, _req_name.name_without_namespace
                            ):
                                name_matched_before = _req_name
                                break

                if not name_matched_before:
                    new_requirements[comp_name] = props
                # we raise name collision error when same name components
                # are introduced at the same level of the component type
                elif (
                    new_requirements[name_matched_before]['__COMPONENT_SOURCE']
                    == props['__COMPONENT_SOURCE']
                ):
                    raise RequirementsProcessingError(
                        'Cannot process component requirements. '
                        'Requirement {} and requirement {} are both added as {}.'
                        "Can't decide which one to pick.".format(
                            name_matched_before.name,
                            comp_name.name,
                            props['__COMPONENT_SOURCE'],
                        )
                    )
                # Give user a info when same name components got overriden
                else:
                    print_info(
                        '{} overrides {} since {} type got higher priority than {}'.format(
                            name_matched_before.name,
                            comp_name.name,
                            new_requirements[name_matched_before]['__COMPONENT_SOURCE'],
                            props['__COMPONENT_SOURCE'],
                        )
                    )

        return new_requirements
