# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
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
from datetime import datetime, timedelta
from io import open
from pathlib import Path

import requests

from idf_component_manager.utils import print_info, print_warn
from idf_component_tools.api_client_errors import APIClientError, NetworkConnectionError, VersionNotFound
from idf_component_tools.archive_tools import pack_archive, unpack_archive
from idf_component_tools.build_system_tools import build_name
from idf_component_tools.errors import FatalError, GitError, ManifestError, NothingToDoError
from idf_component_tools.file_tools import check_unexpected_component_files, copy_filtered_directory, create_directory
from idf_component_tools.git_client import GitClient
from idf_component_tools.hash_tools import (
    HashDoesNotExistError, HashNotEqualError, HashNotSHA256Error, validate_dir_with_hash_file)
from idf_component_tools.manifest import (
    MANIFEST_FILENAME, WEB_DEPENDENCY_REGEX, Manifest, ManifestManager, ProjectRequirements)
from idf_component_tools.semver import SimpleSpec, Version
from idf_component_tools.sources import WebServiceSource

from .cmake_component_requirements import CMakeRequirementsManager, ComponentName, handle_project_requirements
from .context_manager import make_ctx
from .core_utils import (
    ProgressBar, archive_filename, copy_examples_folders, dist_name, parse_example, raise_component_modified_error)
from .dependencies import download_project_dependencies
from .local_component_list import parse_component_list
from .service_details import service_details

try:
    from typing import Optional, Tuple
except ImportError:
    pass

try:
    PROCESSING_TIMEOUT = int(os.getenv('COMPONENT_MANAGER_JOB_TIMEOUT', 300))
except TypeError:
    print_warn(
        'Cannot parse value of COMPONENT_MANAGER_JOB_TIMEOUT.'
        ' It should be number of seconds to wait for job result.')
    PROCESSING_TIMEOUT = 300

CHECK_INTERVAL = 3
MAX_PROGRESS = 100  # Expected progress is in percent


def general_error_handler(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except NetworkConnectionError:
            raise FatalError(
                'Cannot establish a connection to the component registry. Are you connected to the internet?')
        except APIClientError as e:
            raise FatalError(e)

    return wrapper


class ComponentManager(object):
    def __init__(self, path, lock_path=None, manifest_path=None, interface_version=0):
        # type: (str, Optional[str], Optional[str], int) -> None

        # Working directory
        self.path = os.path.abspath(path)

        # Set path of the project's main component
        self.main_component_path = os.path.join(self.path, 'main')

        # Set path of the manifest file for the project's main component
        self.main_manifest_path = manifest_path or (
            os.path.join(path, 'main', MANIFEST_FILENAME) if os.path.isdir(path) else path)

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

        # Components directories
        self.components_path = os.path.join(self.path, 'components')
        self.managed_components_path = os.path.join(self.path, 'managed_components')

        # Dist directory
        self.dist_path = os.path.join(self.path, 'dist')

        self.interface_version = interface_version

    def _get_manifest(self, component='main'):  # type: (str) -> Tuple[str, bool]
        base_dir = self.path if component == 'main' else self.components_path
        manifest_dir = os.path.join(base_dir, component)

        if not os.path.isdir(manifest_dir):
            raise FatalError(
                'Directory "{}" does not exist! '
                'Please specify a valid component under {}'.format(manifest_dir, self.path))

        manifest_filepath = os.path.join(manifest_dir, MANIFEST_FILENAME)
        created = False
        # Create manifest file if it doesn't exist in work directory
        if not os.path.exists(manifest_filepath):
            example_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'templates', 'idf_component_template.yml')
            create_directory(manifest_dir)
            shutil.copyfile(example_path, manifest_filepath)
            print_info('Created "{}"'.format(manifest_filepath))
            created = True
        return manifest_filepath, created

    @general_error_handler
    def create_manifest(self, component='main'):  # type: (str) -> None
        manifest_filepath, created = self._get_manifest(component)
        if not created:
            print_info('"{}" already exists, skipping...'.format(manifest_filepath))

    @general_error_handler
    def create_project_from_example(self, example, path=None, service_profile=None):
        # type: (str, str | None, str | None) -> None

        client, namespace = service_details(None, service_profile, token_required=False)
        component_name, version_spec, example_name = parse_example(example, namespace)
        project_path = path or os.path.join(self.path, os.path.basename(example_name))

        if os.path.isfile(project_path):
            raise FatalError(
                'Your target path is not a directory. Please remove the {} or use different target path.'.format(
                    os.path.abspath(project_path)),
                exit_code=4)

        if os.path.isdir(project_path) and os.listdir(project_path):
            raise FatalError(
                'The directory {} is not empty. To create an example you must empty the directory or '
                'choose a different path.'.format(project_path),
                exit_code=3)

        try:
            component_details = client.component(component_name=component_name, version=version_spec)
        except VersionNotFound as e:
            raise FatalError(e)
        except APIClientError:
            raise FatalError('Selected component "{}" doesn\'t exist.'.format(component_name))

        try:
            example_url = [example for example in component_details.examples if example_name == example['name']][-1]
        except IndexError:
            raise FatalError(
                'Cannot find example "{}" for "{}" version "{}"'.format(example_name, component_name, version_spec),
                exit_code=2)

        response = requests.get(example_url['url'], stream=True)
        with tarfile.open(fileobj=response.raw, mode='r|gz') as tar:
            tar.extractall(project_path)
        print_info('Example "{}" successfully downloaded to {}'.format(example_name, os.path.abspath(project_path)))

    @general_error_handler
    def add_dependency(self, dependency, component='main'):  # type: (str, str) -> None
        manifest_filepath, _ = self._get_manifest(component)

        match = re.match(WEB_DEPENDENCY_REGEX, dependency)
        if match:
            name, spec = match.groups()
        else:
            raise FatalError('Invalid dependency: "{}". Please use format "namespace/name".'.format(dependency))

        if not spec:
            spec = '*'

        try:
            SimpleSpec(spec)
        except ValueError:
            raise FatalError(
                'Invalid dependency version requirement: {}. Please use format like ">=1" or "*".'.format(spec))

        name = WebServiceSource().normalized_name(name)
        manifest_manager = ManifestManager(manifest_filepath, component)
        manifest = manifest_manager.load()

        for dep in manifest.dependencies:
            if dep.name == name:
                raise FatalError('Dependency "{}" already exists for in manifest "{}"'.format(name, manifest_filepath))

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
                "It's likely due to the 4 spaces used for indentation we recommend using 2 spaces indent. "
                'Please check the manifest file:\n{}'.format(manifest_filepath))

        shutil.move(temp_manifest_file.name, manifest_filepath)
        print_info('Successfully added dependency "{}{}" to component "{}"'.format(name, spec, manifest_manager.name))

    @general_error_handler
    def pack_component(self, name, version):  # type: (str, str) -> Tuple[str, Manifest]
        if version == 'git':
            try:
                version = str(GitClient().get_tag_version())
            except GitError:
                raise FatalError('An error happened while getting version from git tag')
        elif version:
            try:
                Version.parse(version)
            except ValueError:
                raise FatalError('Version parameter must be either "git" or a valid semantic version')

        manifest_manager = ManifestManager(self.path, name, check_required_fields=True, version=version)
        manifest = manifest_manager.load()
        dist_temp_dir = Path(self.dist_path, dist_name(manifest))
        include = set(manifest.files['include'])
        exclude = set(manifest.files['exclude'])
        copy_filtered_directory(self.path, str(dist_temp_dir), include=include, exclude=exclude)

        if manifest.examples:
            copy_examples_folders(manifest.examples, Path(self.path), dist_temp_dir, include=include, exclude=exclude)

        manifest_manager.dump(str(dist_temp_dir))

        check_unexpected_component_files(str(dist_temp_dir))

        archive_filepath = os.path.join(self.dist_path, archive_filename(manifest))
        print_info('Saving archive to "{}"'.format(archive_filepath))
        pack_archive(str(dist_temp_dir), archive_filepath)
        return archive_filepath, manifest

    @general_error_handler
    def delete_version(
            self,
            name,  # type: str
            version,  # type: str
            service_profile=None,  # type: str | None
            namespace=None  # type: str | None
    ):  # type: (...) -> None
        client, namespace = service_details(namespace, service_profile)

        if not version:
            raise FatalError('Argument "version" is required')

        component_name = '/'.join([namespace, name])
        # Checking if current version already uploaded
        versions = client.versions(component_name=component_name).versions

        if version not in versions:
            raise NothingToDoError(
                'Version {} of the component "{}" is not on the service'.format(version, component_name))

        client.delete_version(component_name=component_name, component_version=version)
        print_info('Deleted version {} of the component {}'.format(component_name, version))

    @general_error_handler
    def remove_managed_components(self, **kwargs):  # kwargs here to keep idf_extension.py compatibility
        managed_components_dir = Path(self.path, 'managed_components')

        if not managed_components_dir.is_dir():
            return

        undeleted_components = []
        for component_dir in managed_components_dir.glob('*/'):

            if not (managed_components_dir / component_dir).is_dir():
                continue

            try:
                validate_dir_with_hash_file(str(managed_components_dir / component_dir))
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
            allow_existing=False):  # type: (...) -> None
        client, namespace = service_details(namespace, service_profile)
        if archive:
            if not os.path.isfile(archive):
                raise FatalError('Cannot find archive to upload: {}'.format(archive))

            if version:
                raise FatalError('Parameters "version" and "archive" are not supported at the same time')

            tempdir = tempfile.mkdtemp()
            try:
                unpack_archive(archive, tempdir)
                manifest = ManifestManager(tempdir, name, check_required_fields=True).load()
            finally:
                shutil.rmtree(tempdir)
        else:
            archive, manifest = self.pack_component(name, version)

        if not manifest.version:
            raise FatalError('"version" field is required when uploading the component')

        if not manifest.version.is_semver:
            raise FatalError('Only components with semantic versions are allowed on the service')

        if manifest.version.semver.prerelease and skip_pre_release:
            raise NothingToDoError('Skipping pre-release version {}'.format(manifest.version))

        component_name = '/'.join([namespace, manifest.name])
        # Checking if current version already uploaded
        versions = client.versions(component_name=component_name, spec='*').versions
        if manifest.version in versions:
            if allow_existing:
                return

            raise NothingToDoError(
                'Version {} of the component "{}" is already on the service'.format(manifest.version, component_name))

        # Exit if check flag was set
        if check_only:
            return

        # Uploading the component
        print_info('Uploading archive: %s' % archive)
        job_id = client.upload_version(component_name=component_name, file_path=archive)

        # Wait for processing
        print_info(
            'Wait for processing, it is safe to press CTRL+C and exit\n'
            'You can check the state of processing by running CLI command '
            '"compote component upload-status --job=%s"' % job_id)

        timeout_at = datetime.now() + timedelta(seconds=PROCESSING_TIMEOUT)

        try:
            with ProgressBar(total=MAX_PROGRESS, unit='%') as progress_bar:
                while True:
                    if datetime.now() > timeout_at:
                        raise TimeoutError()
                    status = client.task_status(job_id=job_id)
                    progress_bar.set_description(status.message)
                    progress_bar.update_to(status.progress)

                    if status.status == 'failure':
                        raise FatalError("Uploaded version wasn't processed successfully.\n%s" % status.message)
                    elif status.status == 'success':
                        return

                    time.sleep(CHECK_INTERVAL)
        except TimeoutError:
            raise FatalError(
                "Component wasn't processed in {} seconds. Check processing status later.".format(PROCESSING_TIMEOUT))

    @general_error_handler
    def upload_component_status(self, job_id, service_profile=None):  # type: (str, str | None) -> None
        client, _ = service_details(None, service_profile)
        status = client.task_status(job_id=job_id)
        if status.status == 'failure':
            raise FatalError("Uploaded version wasn't processed successfully.\n%s" % status.message)
        else:
            print_info('Status: %s. %s' % (status.status, status.message))

    @general_error_handler
    def prepare_dep_dirs(self, managed_components_list_file, component_list_file, local_components_list_file=None):
        '''Process all manifests and download all dependencies'''
        # Find all components
        local_components = []
        if local_components_list_file and os.path.isfile(local_components_list_file):
            local_components = parse_component_list(local_components_list_file)
        else:
            local_components.append({'name': 'main', 'path': self.main_component_path})

            if os.path.isdir(self.components_path):
                local_components.extend(
                    {
                        'name': item,
                        'path': os.path.join(self.components_path, item)
                    } for item in os.listdir(self.components_path)
                    if os.path.isdir(os.path.join(self.components_path, item)))

        # Check that CMakeLists.txt and idf_component.yml exists for all component dirs
        local_components = [
            component for component in local_components
            if os.path.isfile(os.path.join(component['path'], 'CMakeLists.txt'))
            and os.path.isfile(os.path.join(component['path'], MANIFEST_FILENAME))
        ]

        downloaded_component_paths = set()
        if local_components:
            manifests = []

            for component in local_components:
                manifest_filepath = os.path.join(component['path'], MANIFEST_FILENAME)
                with make_ctx('manifest', manifest_path=manifest_filepath):
                    manifests.append(ManifestManager(component['path'], component['name']).load())

            project_requirements = ProjectRequirements(manifests)
            downloaded_component_paths, downloaded_component_version_dict = download_project_dependencies(
                project_requirements, self.lock_path, self.managed_components_path)

        # Exclude requirements paths
        downloaded_component_paths -= {component['path'] for component in local_components}
        # Change relative paths to absolute paths
        downloaded_component_paths = {os.path.abspath(path) for path in list(downloaded_component_paths)}
        # Include managed components in project directory
        with open(managed_components_list_file, mode='w', encoding='utf-8') as file:
            for component_path in downloaded_component_paths:
                file.write(u'idf_build_component("%s")\n' % Path(component_path).as_posix())
                component_name = Path(component_path).name
                file.write(
                    u'idf_component_set_property(%s %s "%s")\n' %
                    (component_name, 'COMPONENT_VERSION', downloaded_component_version_dict[component_path]))

            component_names = ';'.join(os.path.basename(path) for path in downloaded_component_paths)
            file.write(u'set(managed_components "%s")\n' % component_names)

        # Saving list of all components with manifests for use on requirements injection step
        all_components = downloaded_component_paths.union(component['path'] for component in local_components)
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
            raise FatalError('Cannot find component list file. Please make sure this script is executed from CMake')

        add_all_components_to_main = False
        for component in components_with_manifests:
            component = component.strip()
            name = os.path.basename(component)
            manifest = ManifestManager(component, name).load()
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
        # to reproduce convenience behavior for the standard project defined in IDF's `project.cmake`
        # For ESP-IDF < 5.0 (Remove after ESP-IDF 4.4 EOL)
        if add_all_components_to_main:
            main_reqs = requirements[ComponentName('idf', 'main')]['REQUIRES']
            for requirement in requirements.keys():
                name = requirement.name
                if name not in main_reqs and name != 'main' and isinstance(main_reqs, list):
                    main_reqs.append(name)

        handle_project_requirements(requirements)
        requirements_manager.dump(requirements)
