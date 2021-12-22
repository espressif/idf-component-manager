"""Core module of component manager"""
from __future__ import print_function

import os
import re
import shutil
import tempfile
import time
from datetime import datetime, timedelta
from io import open
from pathlib import Path

from semantic_version import SimpleSpec, Version
from tqdm import tqdm

from idf_component_tools.api_client import APIClientError
from idf_component_tools.archive_tools import pack_archive, unpack_archive
from idf_component_tools.build_system_tools import build_name
from idf_component_tools.errors import FatalError, GitError, ManifestError, NothingToDoError
from idf_component_tools.file_tools import copy_filtered_directory, create_directory
from idf_component_tools.git_client import GitClient
from idf_component_tools.manifest import (
    MANIFEST_FILENAME, WEB_DEPENDENCY_REGEX, Manifest, ManifestManager, ProjectRequirements)
from idf_component_tools.sources import WebServiceSource

from .cmake_component_requirements import ITERABLE_PROPS, CMakeRequirementsManager, ComponentName
from .core_utils import archive_filename, dist_name
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
    print(
        'WARNING: Cannot parse value of COMPONENT_MANAGER_JOB_TIMEOUT.'
        ' It should be number of seconds to wait for job result.')
    PROCESSING_TIMEOUT = 300

CHECK_INTERVAL = 3
MAX_PROGRESS = 100  # Expected progress is in percent


class ComponentManager(object):
    def __init__(self, path, lock_path=None, manifest_path=None):
        # type: (str, Optional[str], Optional[str]) -> None

        # Working directory
        self.path = os.path.abspath(path if os.path.isdir(path) else os.path.dirname(path))

        # Set path of the project's main component
        self.main_component_path = os.path.join(self.path, 'main')

        # Set path of the manifest file for the project's main component
        self.main_manifest_path = manifest_path or (
            os.path.join(path, 'main', MANIFEST_FILENAME) if os.path.isdir(path) else path)

        # Lock path
        self.lock_path = lock_path or (os.path.join(path, 'dependencies.lock') if os.path.isdir(path) else path)

        # Components directories
        self.components_path = os.path.join(self.path, 'components')
        self.managed_components_path = os.path.join(self.path, 'managed_components')

        # Dist directory
        self.dist_path = os.path.join(self.path, 'dist')

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
            print('Created "{}"'.format(manifest_filepath))
            created = True
        return manifest_filepath, created

    def create_manifest(self, args):
        manifest_filepath, created = self._get_manifest(args.get('component', 'main'))
        if not created:
            print('"{}" already exists, skipping...'.format(manifest_filepath))

    def add_dependency(self, args):
        dependency = args.get('dependency')
        manifest_filepath, _ = self._get_manifest(args.get('component', 'main'))

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
        manifest_manager = ManifestManager(manifest_filepath, args.get('component'))
        manifest = manifest_manager.load()

        for dependency in manifest.dependencies:
            if dependency.name == name:
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
        print('Successfully added dependency "{}{}" for component "{}"'.format(name, spec, manifest_manager.name))

    def pack_component(self, args):  # type: (dict) -> Tuple[str, Manifest]
        version = args.get('version')

        if version == 'git':
            try:
                version = GitClient().get_tag_version()
            except GitError:
                raise FatalError('An error happend while getting version from git tag')
        elif version:
            try:
                Version.parse(version)
            except ValueError:
                raise FatalError('Version parameter must be either "git" or a valid semantic version')

        manifest_manager = ManifestManager(self.path, args['name'], check_required_fields=True, version=version)
        manifest = manifest_manager.load()
        dist_temp_dir = os.path.join(self.dist_path, dist_name(manifest))
        copy_filtered_directory(
            self.path, dist_temp_dir, include=set(manifest.files['include']), exclude=set(manifest.files['exclude']))
        manifest_manager.dump(dist_temp_dir)
        archive_filepath = os.path.join(self.dist_path, archive_filename(manifest))
        print('Saving archive to "{}"'.format(archive_filepath))
        pack_archive(dist_temp_dir, archive_filepath)
        return archive_filepath, manifest

    def delete_version(self, args):
        client, namespace = service_details(args.get('namespace'), args.get('service_profile'))
        name = args.get('name')
        version = args.get('version')

        if not version:
            raise FatalError('Argument "version" is required')

        component_name = '/'.join([namespace, name])
        # Checking if current version already uploaded
        versions = client.versions(component_name).versions

        if version not in versions:
            raise NothingToDoError(
                'Version {} of the component "{}" is not on the service'.format(version, component_name))

        try:
            client.delete_version(component_name=component_name, component_version=version)
            print('Deleted version {} of the component {}'.format(component_name, version))
        except APIClientError as e:
            raise FatalError(e)

    def upload_component(self, args):
        client, namespace = service_details(args.get('namespace'), args.get('service_profile'))
        version = args.get('version')
        archive_file = args.get('archive')
        if archive_file:
            if not os.path.isfile(archive_file):
                raise FatalError('Cannot find archive to upload: {}'.format(archive_file))

            if version:
                raise FatalError('Parameters "version" and "archive" are not supported at the same time')

            tempdir = tempfile.mkdtemp()
            try:
                unpack_archive(archive_file, tempdir)
                manifest = ManifestManager(tempdir, args['name'], check_required_fields=True).load()
            finally:
                shutil.rmtree(tempdir)
        else:
            archive_file, manifest = self.pack_component(args)

        if not manifest.version.is_semver:
            raise FatalError('Only components with semantic versions are allowed on the service')

        if manifest.version.semver.prerelease and args.get('skip_pre_release'):
            raise NothingToDoError('Skipping pre-release version {}'.format(manifest.version))

        try:
            component_name = '/'.join([namespace, manifest.name])
            # Checking if current version already uploaded
            versions = client.versions(component_name, spec='*').versions
            if manifest.version in versions:
                if args.get('allow_existing'):
                    return

                raise NothingToDoError(
                    'Version {} of the component "{}" is already on the service'.format(
                        manifest.version, component_name))

            # Exit if check flag was set
            if args.get('check_only'):
                return

            # Uploading the component
            print('Uploading archive: %s' % archive_file)
            job_id = client.upload_version(component_name=component_name, file_path=archive_file)

            # Wait for processing
            print(
                'Wait for processing, it is safe to press CTRL+C and exit\n'
                'You can check the state of processing by running subcommand '
                '"upload-component-status --job=%s"' % job_id)

            timeout_at = datetime.now() + timedelta(seconds=PROCESSING_TIMEOUT)

            try:
                with tqdm(total=MAX_PROGRESS, unit='%') as progress_bar:
                    while True:
                        if datetime.now() > timeout_at:
                            raise TimeoutError()
                        status = client.task_status(job_id)
                        progress_bar.set_description(status.message)
                        progress_bar.update(status.progress)

                        if status.status == 'failure':
                            raise FatalError("Uploaded version wasn't processed successfully.\n%s" % status.message)
                        elif status.status == 'success':
                            return

                        time.sleep(CHECK_INTERVAL)
            except TimeoutError:
                raise FatalError(
                    "Component wasn't processed in {} seconds. Check processing status later.".format(
                        PROCESSING_TIMEOUT))

        except APIClientError as e:
            raise FatalError(e)

    def upload_component_status(self, args):
        job_id = args.get('job')

        if not job_id:
            raise FatalError('Job ID is required')

        client, _ = service_details(None, args.get('service_profile'))
        try:
            status = client.task_status(job_id)
            if status.status == 'failure':
                raise FatalError("Uploaded version wasn't processed successfully.\n%s" % status.message)
            else:
                print('Status: %s. %s' % (status.status, status.message))

        except APIClientError as e:
            raise FatalError(e)

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
            manifests = [ManifestManager(component['path'], component['name']).load() for component in local_components]
            project_requirements = ProjectRequirements(manifests)
            downloaded_component_paths = download_project_dependencies(
                project_requirements, self.lock_path, self.managed_components_path)

        # Exclude requirements paths
        downloaded_component_paths -= {component['path'] for component in local_components}
        # Change relative paths to absolute paths
        downloaded_component_paths = {os.path.abspath(path) for path in list(downloaded_component_paths)}
        # Include managed components in project directory
        with open(managed_components_list_file, mode='w', encoding='utf-8') as file:
            for component_path in downloaded_component_paths:
                file.write(u'idf_build_component("%s")\n' % Path(component_path).as_posix())

            component_names = ';'.join(os.path.basename(path) for path in downloaded_component_paths)
            file.write(u'set(managed_components "%s")\n' % component_names)

        # Saving list of all components with manifests for use on requirements injection step
        all_components = downloaded_component_paths.union(component['path'] for component in local_components)
        with open(component_list_file, mode='w', encoding='utf-8') as file:
            file.write(u'\n'.join(all_components))

    def inject_requirements(self, component_requires_file, component_list_file):
        '''Set build dependencies for components with manifests'''
        requirements_manager = CMakeRequirementsManager(component_requires_file)
        requirements = requirements_manager.load()

        try:
            with open(component_list_file, mode='r', encoding='utf-8') as f:
                components_with_manifests = f.readlines()
            os.remove(component_list_file)
        except FileNotFoundError:
            raise FatalError('Cannot find component list file. Please make sure this script is executed from CMake')

        for component in components_with_manifests:
            component = component.strip()
            name = os.path.basename(component)
            manifest = ManifestManager(component, name).load()
            name_key = ComponentName('idf', name)

            for dependency in manifest.dependencies:
                if dependency.meta:
                    continue

                dependency_name = build_name(dependency.name)
                requirement_key = 'REQUIRES' if dependency.public else 'PRIV_REQUIRES'

                # Don't add requirements to the main component
                # to let it be handled specially by the IDF build system
                if name_key == ComponentName('idf', 'main'):
                    if dependency.public is False:
                        print(
                            'WARNING: Public flag is ignored for the main dependency "{}". '
                            'All dependencies of the main component are always public.'.format(dependency.name))
                    continue

                if dependency_name not in requirements[name_key][requirement_key]:
                    requirements[name_key][requirement_key].append(dependency_name)

        # Handling "unknown" dependencies
        known_names = [component_name.name for component_name in requirements.keys()]
        for name, requirement in requirements.items():
            for prop in ITERABLE_PROPS:
                if prop not in requirement:
                    continue

                items = requirement[prop]
                for index, item in enumerate(items):
                    # Skip if known
                    if item in known_names:
                        continue

                    # Replace requirement for components installed by the manager
                    prefixed_name = '__{}'.format(item)
                    for known_name in known_names:
                        if not known_name.endswith(prefixed_name):
                            continue

                        if known_name in items:
                            del items[index]
                        else:
                            items[index] = known_name

                requirements[name][prop] = items

        requirements_manager.dump(requirements)
