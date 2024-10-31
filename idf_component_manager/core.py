# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Core module of component manager"""

import functools
import os
import re
import shutil
import tarfile
import tempfile
import time
import typing as t
from collections import OrderedDict
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import requests
from requests_toolbelt import MultipartEncoderMonitor

from idf_component_manager.utils import ComponentSource
from idf_component_tools import ComponentManagerSettings
from idf_component_tools.archive_tools import pack_archive, unpack_archive
from idf_component_tools.build_system_tools import build_name, is_component
from idf_component_tools.config import root_managed_components_dir
from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.errors import (
    FatalError,
    InternalError,
    ManifestError,
    NothingToDoError,
    VersionAlreadyExistsError,
    VersionNotFoundError,
)
from idf_component_tools.file_tools import (
    copy_filtered_directory,
)
from idf_component_tools.git_client import GitClient, clean_tag_version
from idf_component_tools.hash_tools.errors import (
    HashDoesNotExistError,
    HashNotEqualError,
    HashNotSHA256Error,
)
from idf_component_tools.hash_tools.validate_managed_component import (
    validate_managed_component_hash,
)
from idf_component_tools.manager import (
    ManifestManager,
    UploadMode,
)
from idf_component_tools.manifest import (
    WEB_DEPENDENCY_REGEX,
    Manifest,
)
from idf_component_tools.messages import notice, warn
from idf_component_tools.registry.client_errors import (
    APIClientError,
    ComponentNotFound,
    NetworkConnectionError,
    VersionNotFound,
)
from idf_component_tools.registry.service_details import (
    get_api_client,
    get_storage_client,
)
from idf_component_tools.semver import SimpleSpec, Version
from idf_component_tools.sources import GitSource, WebServiceSource
from idf_component_tools.utils import ProjectRequirements

from .cmake_component_requirements import (
    CMakeRequirementsManager,
    ComponentName,
    RequirementsProcessingError,
    check_requirements_name_collisions,
    handle_project_requirements,
)
from .core_utils import (
    ProgressBar,
    _create_manifest_if_missing,
    archive_filename,
    copy_examples_folders,
    dist_name,
    get_validated_manifest,
    parse_example,
    raise_component_modified_error,
)
from .dependencies import download_project_dependencies
from .local_component_list import parse_component_list
from .sync import sync_components

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


class ComponentManager:
    def __init__(
        self,
        path: str,
        lock_path: t.Optional[str] = None,
        manifest_path: t.Optional[str] = None,
        interface_version: int = 0,
    ) -> None:
        # Working directory
        self.path = Path(path).resolve()

        # Set path of the project's main component
        self.main_component_path = self.path / 'main'

        # Set path of the manifest file for the project's main component
        if not manifest_path:
            self.main_manifest_path = (
                self.path / 'main' / MANIFEST_FILENAME if self.path.is_dir() else self.path
            )
        else:
            self.main_manifest_path = Path(manifest_path)

        # Lock path
        if not lock_path:
            self.lock_path = self.path if self.path.is_file() else self.path / 'dependencies.lock'
        elif os.path.isabs(lock_path):
            self.lock_path = Path(lock_path)
        else:
            self.lock_path = self.path / lock_path

        # Components directories
        self.components_path = self.path / 'components'
        self.managed_components_path = self.path / 'managed_components'

        # Dist directory
        self.default_dist_path = self.path / 'dist'

        self.interface_version = interface_version

    def _get_manifest_dir(self, component: str = 'main', path: t.Optional[str] = None) -> str:
        if component != 'main' and path is not None:
            raise FatalError(
                'Cannot determine manifest directory. Please specify either component or path.'
            )

        # If path is specified
        if path is not None:
            manifest_dir = Path(path).resolve()
        # If the current working directory is in the context of a component
        elif is_component(Path.cwd()):
            manifest_dir = Path.cwd()
        else:
            # If the current working directory is in the context of a project
            base_dir = self.path if component == 'main' else self.components_path
            manifest_dir = base_dir / component

        if not manifest_dir.is_dir():
            raise FatalError(
                'Directory "{}" does not exist! '
                'Please specify a valid component under {} or try to use --path'.format(
                    manifest_dir, self.path
                )
            )
        if not manifest_dir.as_posix().startswith(self.path.as_posix()):
            raise FatalError(
                'Directory "{}" is not under project directory! '
                'Please specify a valid component under {}'.format(manifest_dir, self.path)
            )

        return manifest_dir.as_posix()

    @property
    @lru_cache(1)
    def root_managed_components_dir(self) -> str:
        return str(root_managed_components_dir())

    @property
    @lru_cache(1)
    def root_managed_components_lock_path(self) -> str:
        return os.path.join(self.root_managed_components_dir, 'dependencies.lock')

    def _get_manifest(
        self, component: str = 'main', path: t.Optional[str] = None
    ) -> t.Tuple[str, bool]:
        manifest_dir = self._get_manifest_dir(component=component, path=path)
        manifest_filepath = Path(manifest_dir) / MANIFEST_FILENAME
        # Create manifest file if it doesn't exist in work directory
        manifest_created = _create_manifest_if_missing(Path(manifest_dir))
        return manifest_filepath.as_posix(), manifest_created

    @general_error_handler
    def create_manifest(self, component: str = 'main', path: t.Optional[str] = None) -> None:
        manifest_filepath, created = self._get_manifest(component=component, path=path)
        if not created:
            notice(f'"{manifest_filepath}" already exists, skipping...')

    @general_error_handler
    def create_project_from_example(
        self,
        example: str,
        path: t.Optional[str] = None,
        profile_name: t.Optional[str] = None,
    ) -> None:
        client = get_storage_client(profile_name=profile_name)
        component_name, version_spec, example_name = parse_example(
            example, client.default_namespace
        )
        project_path = Path(path) if path else self.path / os.path.basename(example_name)

        if project_path.is_file():
            raise FatalError(
                'Your target path is not a directory. '
                'Please remove the {} or use different target path.'.format(project_path.resolve()),
                exit_code=4,
            )

        if project_path.is_dir() and any(project_path.iterdir()):
            raise FatalError(
                f'The directory {project_path} is not empty. '
                'To create an example you must empty the directory or '
                'choose a different path.',
                exit_code=3,
            )

        component_details = client.component(component_name=component_name, version=version_spec)

        try:
            example_url = [
                example
                for example in component_details['examples']
                if example_name == example['name']
            ][-1]
        except IndexError:
            raise FatalError(
                f'Cannot find example "{example_name}" for "{component_name}" '
                f'version "{version_spec}"',
                exit_code=2,
            )

        response = requests.get(example_url['url'], stream=True)  # noqa: S113
        with tarfile.open(fileobj=response.raw, mode='r|gz') as tar:
            tar.extractall(project_path)  # noqa: S202
        notice(
            'Example "{}" successfully downloaded to {}'.format(
                example_name, project_path.resolve()
            )
        )

    @general_error_handler
    def add_dependency(
        self,
        dependency: str,
        component: str = 'main',
        path: t.Optional[str] = None,
        profile_name: t.Optional[str] = None,
        git: t.Optional[str] = None,
        git_path: str = '.',
        git_ref: t.Optional[str] = None,
    ) -> None:
        manifest_filepath, _ = self._get_manifest(component=component, path=path)

        if path is not None:
            component_path = Path(path).resolve()
            component = os.path.basename(component_path)
        # If the path refers to a component context
        # we need to use the components name as the component
        elif is_component(Path.cwd()):
            component = os.path.basename(self.path)

        if git:
            name = dependency
            GitSource(git=git, path=git_path).exists(git_ref)
        else:
            match = re.match(WEB_DEPENDENCY_REGEX, dependency)
            if match:
                name, spec = match.groups()
            else:
                raise FatalError(
                    f'Invalid dependency: "{dependency}". Please use format "namespace/name".'
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
            # make sure it exists in the registry's storage url
            client = get_storage_client(profile_name=profile_name).registry_storage_client
            if not client:
                raise InternalError()

            client.component(component_name=name, version=spec)

        manifest_manager = ManifestManager(manifest_filepath, component)
        manifest = manifest_manager.load()

        for dep in manifest.raw_requirements:
            if dep.name == name:
                raise FatalError(
                    'Dependency "{}" already exists for in manifest "{}"'.format(
                        name, manifest_filepath
                    )
                )

        with open(manifest_filepath, encoding='utf-8') as file:
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

        if git:
            file_lines.insert(index, f'  {name}:\n')
            file_lines.insert(index + 1, f'    git: "{git}"\n')
            index = index + 2
            if git_path:
                file_lines.insert(index, f'    path: "{git_path}"\n')
                index = index + 1
            if git_ref:
                file_lines.insert(index, f'    version: "{git_ref}"\n')
        else:
            file_lines.insert(index, f'  {name}: "{spec}"\n')

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
        if git:
            notice(
                'Successfully added git dependency "{}" to component "{}"'.format(
                    name, manifest_manager.name
                )
            )
        else:
            notice(
                'Successfully added dependency "{}{}" to component "{}"'.format(
                    name, spec, manifest_manager.name
                )
            )

    @general_error_handler
    def pack_component(
        self,
        name: str,
        version: t.Optional[str] = None,
        dest_dir: t.Optional[str] = None,
        repository: t.Optional[str] = None,
        commit_sha: t.Optional[str] = None,
        repository_path: t.Optional[str] = None,
    ) -> t.Tuple[str, Manifest]:
        dest_path = self.path / dest_dir if dest_dir else self.default_dist_path

        if version == 'git':
            version = str(GitClient().get_tag_version(cwd=self.path))
        elif version:
            try:
                # In CI the version can come from a git tag, handle it with the same logic
                version = clean_tag_version(version)
                Version.parse(version)
            except ValueError:
                raise FatalError(
                    'Version parameter must be either "git" or a valid version.\n'
                    'Received: "{}"\n'
                    'Documentation: https://docs.espressif.com/projects/idf-component-manager/en/'
                    'latest/reference/versioning.html#versioning-scheme'.format(version)
                )

        manifest_manager = ManifestManager(
            self.path.as_posix(),
            name,
            upload_mode=UploadMode.component,
            version=version,
            repository=repository,
            commit_sha=commit_sha,
            repository_path=repository_path,
        )
        manifest = manifest_manager.load()
        dest_temp_dir = dest_path / dist_name(name, manifest.version)
        exclude_set = manifest.exclude_set

        # If a custom directory is defined, add it to the set of files to exclude
        if dest_dir is not None:
            exclude_set.add(os.path.relpath(dest_path, self.path) + '/**/*')

        copy_filtered_directory(
            self.path.as_posix(),
            dest_temp_dir.as_posix(),
            use_gitignore=manifest.use_gitignore,
            include=manifest.include_set,
            exclude=exclude_set,
        )

        if manifest.examples:
            copy_examples_folders(
                manifest.examples,
                Path(self.path),
                dest_temp_dir,
                use_gitignore=manifest.use_gitignore,
                include=manifest.include_set,
                exclude=manifest.exclude_set,
            )

        manifest_manager.dump(str(dest_temp_dir))

        get_validated_manifest(manifest_manager, str(dest_temp_dir))

        archive_filepath = os.path.join(dest_path, archive_filename(name, manifest.version))
        notice(f'Saving archive to "{archive_filepath}"')
        pack_archive(str(dest_temp_dir), archive_filepath)
        return archive_filepath, manifest

    @general_error_handler
    def delete_version(
        self,
        name: str,
        version: str,
        profile_name: t.Optional[str] = None,
        namespace: t.Optional[str] = None,
    ) -> None:
        if not version:
            raise FatalError('Argument "version" is required')

        api_client = get_api_client(namespace=namespace, profile_name=profile_name)
        component_name = '/'.join([api_client.default_namespace, name])

        # Checking if current version already uploaded
        versions = api_client.versions(component_name=component_name).versions

        if version not in versions:
            raise VersionNotFoundError(
                'Version {} of the component "{}" is not on the registry'.format(
                    version, component_name
                )
            )

        api_client.delete_version(component_name=component_name, component_version=version)
        notice(f'Deleted version {version} of the component {component_name}')

    @general_error_handler
    def yank_version(
        self,
        name: str,
        version: str,
        message: str,
        profile_name: t.Optional[str] = None,
        namespace: t.Optional[str] = None,
    ):
        api_client = get_api_client(namespace=namespace, profile_name=profile_name)
        component_name = '/'.join([api_client.default_namespace, name])

        versions = api_client.versions(component_name=component_name).versions

        if version not in versions:
            raise VersionNotFoundError(
                'Version {} of the component "{}" is not on the registry'.format(
                    version, component_name
                )
            )

        api_client.yank_version(
            component_name=component_name,
            component_version=version,
            yank_message=message,
        )
        notice(
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
        name: str,
        version: t.Optional[str] = None,
        profile_name: t.Optional[str] = None,
        namespace: t.Optional[str] = None,
        archive: t.Optional[str] = None,
        skip_pre_release: bool = False,
        check_only: bool = False,
        allow_existing: bool = False,
        dry_run: bool = False,
        dest_dir: t.Optional[str] = None,
        repository: t.Optional[str] = None,
        commit_sha: t.Optional[str] = None,
        repository_path: t.Optional[str] = None,
    ) -> None:
        """
        Uploads a component version to the registry.
        """
        api_client = get_api_client(namespace=namespace, profile_name=profile_name)

        if archive:
            if not os.path.isfile(archive):
                raise FatalError(f'Cannot find archive to upload: {archive}')

            if version:
                raise FatalError(
                    'Parameters "version" and "archive" are not supported at the same time'
                )

            tempdir = tempfile.mkdtemp()
            try:
                unpack_archive(archive, tempdir)
                manifest_manager = ManifestManager(
                    tempdir,
                    name,
                    upload_mode=UploadMode.component,
                    repository=repository,
                    commit_sha=commit_sha,
                    repository_path=repository_path,
                )
                manifest = get_validated_manifest(manifest_manager, tempdir)
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

        if manifest.version.semver.prerelease and skip_pre_release:
            raise NothingToDoError(f'Skipping pre-release version {manifest.version}')

        component_name = '/'.join([api_client.default_namespace, name])
        # Checking if current version already uploaded
        try:
            versions = api_client.versions(component_name=component_name, spec='*').versions

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
        notice(f'{info_message} archive {archive}')

        file_stat = os.stat(archive)  # type: ignore
        with ProgressBar(
            total=file_stat.st_size, unit='B', unit_scale=True, leave=False
        ) as progress_bar:
            memo = {'progress': 0}

            def callback(monitor: MultipartEncoderMonitor) -> None:
                progress_bar.update(monitor.bytes_read - memo['progress'])
                memo['progress'] = monitor.bytes_read

            if dry_run:
                job_id = api_client.validate_version(file_path=archive, callback=callback)
            else:
                job_id = api_client.upload_version(
                    component_name=component_name, file_path=archive, callback=callback
                )

            progress_bar.close()

        # Wait for processing
        profile_text = (
            ''
            if profile_name is None or profile_name == 'default'
            else f' --profile={profile_name}'
        )
        notice(
            'Wait for processing, it is safe to press CTRL+C and exit\n'
            'You can check the state of processing by running CLI command '
            '"compote component upload-status --job={} {}"'.format(job_id, profile_text)
        )
        upload_timeout = ComponentManagerSettings().VERSION_PROCESS_TIMEOUT
        timeout_at = datetime.now() + timedelta(seconds=upload_timeout)

        try:
            warnings = set()
            with ProgressBar(total=MAX_PROGRESS, unit='%', leave=False) as progress_bar:
                while True:
                    if datetime.now() > timeout_at:
                        raise TimeoutError()
                    status = api_client.task_status(job_id=job_id)

                    for warning in status.warnings:
                        if warning not in warnings:
                            warnings.add(warning)

                    if status.status == 'failure' or status.status == 'success':
                        progress_bar.close()
                        for warning in warnings:
                            warn(warning)

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
                        notice(status.message)
                        return

                    progress_bar.set_description(status.message)
                    progress_bar.update_to(status.progress)

                    time.sleep(CHECK_INTERVAL)
        except TimeoutError:
            raise FatalError(
                f"Component wasn't processed in {upload_timeout} seconds. "
                'Check processing status later.'
            )

    @general_error_handler
    def upload_component_status(self, job_id: str, profile_name: t.Optional[str] = None) -> None:
        api_client = get_api_client(profile_name=profile_name)
        status = api_client.task_status(job_id=job_id)
        if status.status == 'failure':
            raise FatalError(f"Uploaded version wasn't processed successfully.\n{status.message}")
        else:
            notice(f'Status: {status.status}. {status.message}')

    def update_dependencies(self, **kwargs):
        if self.lock_path.is_file():
            os.remove(self.lock_path)

    # Function executed from CMake

    @general_error_handler
    def prepare_dep_dirs(
        self,
        managed_components_list_file,
        component_list_file,
        local_components_list_file=None,
    ):
        """Process all manifests and download all dependencies"""
        # root core components
        root_manifest_filepath = root_managed_components_dir() / MANIFEST_FILENAME
        if root_manifest_filepath.is_file():
            root_managed_components = download_project_dependencies(
                ProjectRequirements([
                    ManifestManager(
                        self.root_managed_components_dir,
                        'root',
                    ).load()
                ]),
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
            local_components.append({'name': 'main', 'path': self.main_component_path.as_posix()})

            if os.path.isdir(self.components_path):
                local_components.extend(
                    {'name': item, 'path': item.as_posix()}
                    for item in self.components_path.iterdir()
                    if item.is_dir()
                )

        # Check that CMakeLists.txt and idf_component.yml exists for all component dirs
        local_components = [
            component
            for component in local_components
            if os.path.isfile(os.path.join(component['path'], 'CMakeLists.txt'))
            and os.path.isfile(os.path.join(component['path'], MANIFEST_FILENAME))
        ]

        downloaded_components = set()
        manifests = []
        if local_components:
            for component in local_components:
                manifests.append(
                    ManifestManager(
                        component['path'],
                        component['name'],
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
        # order is important, since kconfig items are processed in order
        downloaded_components = sorted(downloaded_components)
        root_managed_components = sorted(root_managed_components)
        all_managed_components = sorted(set(downloaded_components + root_managed_components))

        with open(managed_components_list_file, mode='w', encoding='utf-8') as file:
            # Set versions for manifests in requierements too
            # It's useful in the case when the component was moved from `managed_components`
            # to `components`
            for requirement in manifests:
                if requirement.version:
                    file.write(
                        'idf_component_set_property({} {} "{}")\n'.format(
                            requirement.name,
                            'COMPONENT_VERSION',
                            requirement.version,
                        )
                    )

            for is_root, group in enumerate([downloaded_components, root_managed_components]):
                for downloaded_component in group:
                    file.write(
                        'idf_build_component("{}" "{}")\n'.format(
                            downloaded_component.abs_posix_path,
                            ('idf_components' if is_root == 1 else 'project_managed_components'),
                        )
                    )
                    file.write(
                        'idf_component_set_property({} {} "{}")\n'.format(
                            downloaded_component.name,
                            'COMPONENT_VERSION',
                            downloaded_component.version,
                        )
                    )

                    if downloaded_component.targets:
                        file.write(
                            'idf_component_set_property({} {} "{}")\n'.format(
                                downloaded_component.name,
                                'REQUIRED_IDF_TARGETS',
                                ' '.join(downloaded_component.targets),
                            )
                        )

            file.write(
                'set(managed_components "%s")\n'
                % ';'.join(component.name for component in all_managed_components)
            )

        # Saving list of all components with manifests for use on requirements injection step
        all_components = sorted(
            {component.abs_path for component in all_managed_components}.union(
                component['path'] for component in local_components
            )
        )
        with open(component_list_file, mode='w', encoding='utf-8') as file:
            file.write('\n'.join(all_components))

    @general_error_handler
    def inject_requirements(
        self,
        component_requires_file: t.Union[Path, str],
        component_list_file: t.Union[Path, str],
    ):
        """Set build dependencies for components with manifests"""
        requirements_manager = CMakeRequirementsManager(component_requires_file)
        requirements = requirements_manager.load()

        try:
            with open(component_list_file, encoding='utf-8') as f:
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
            manifest = ManifestManager(component, name).load()
            name_key = ComponentName('idf', name)

            for dep in manifest.requirements:
                # Meta dependencies, like 'idf' are not used directly
                if dep.meta:
                    continue

                # No required dependencies shouldn't be added to the build system
                if not dep.is_required:
                    continue

                dependency_name = build_name(dep.name)
                requirement_key = 'REQUIRES' if dep.is_public else 'PRIV_REQUIRES'

                def add_req(key: str) -> None:
                    if key not in requirements[name_key]:
                        requirements[name_key][key] = []

                    req = requirements[name_key][key]
                    if isinstance(req, list) and dependency_name not in req:
                        req.append(dependency_name)

                add_req(requirement_key)

                managed_requirement_key = f'MANAGED_{requirement_key}'
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
        requirements: t.OrderedDict[ComponentName, t.Dict[str, t.Union[t.List[str], str]]],
    ) -> t.OrderedDict[ComponentName, t.Dict[str, t.Union[t.List[str], str]]]:
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
                raise InternalError()

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
                # Give user an info when same name components got overriden
                else:
                    notice(
                        '{} overrides {} since {} type got higher priority than {}'.format(
                            name_matched_before.name,
                            comp_name.name,
                            new_requirements[name_matched_before]['__COMPONENT_SOURCE'],
                            props['__COMPONENT_SOURCE'],
                        )
                    )

        return new_requirements

    def sync_registry(
        self,
        profile_name: str,
        save_path: t.Union[str, Path],
        interval: int = 0,
        components: t.Optional[t.List[str]] = None,
        recursive: bool = True,
    ) -> None:
        client = get_storage_client(profile_name=profile_name)
        save_path = Path(save_path)
        if interval:
            while True:
                sync_components(client, self.path, save_path, components, recursive)
                time.sleep(interval)
        else:
            sync_components(client, self.path, save_path, components, recursive)
