"""Core module of component manager"""
from __future__ import print_function

import os
import shutil
import tempfile
from io import open
from pathlib import Path

from idf_component_tools.api_client import APIClientError
from idf_component_tools.archive_tools import pack_archive, unpack_archive
from idf_component_tools.build_system_tools import build_name
from idf_component_tools.errors import FatalError, NothingToDoError
from idf_component_tools.file_tools import create_directory
from idf_component_tools.manifest import ManifestManager

from .cmake_component_requirements import CMakeRequirementsManager, ComponentName
from .dependencies import download_project_dependencies
from .local_component_list import parse_component_list
from .service_details import service_details

try:
    from typing import Optional
except ImportError:
    pass


class ComponentManager(object):
    def __init__(self, path, lock_path=None, manifest_path=None):
        # type: (str, Optional[str], Optional[str]) -> None

        # Working directory
        self.path = os.path.abspath(path if os.path.isdir(path) else os.path.dirname(path))

        # Set path of the project's main component
        self.main_component_path = os.path.join(self.path, 'main')

        # Set path of the manifest file for the project's main component
        self.main_manifest_path = manifest_path or (
            os.path.join(path, 'main', 'idf_component.yml') if os.path.isdir(path) else path)

        # Lock path
        self.lock_path = lock_path or (os.path.join(path, 'dependencies.lock') if os.path.isdir(path) else path)

        # Components directories
        self.components_path = os.path.join(self.path, 'components')
        self.managed_components_path = os.path.join(self.path, 'managed_components')

        # Dist directory
        self.dist_path = os.path.join(self.path, 'dist')

    def create_manifest(self, args):
        """Create manifest file if it doesn't exist in work directory"""
        if os.path.exists(self.main_manifest_path):
            print('`idf_component.yml` already exists in main component directory, skipping...')
        else:
            example_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'templates', 'idf_component_template.yml')
            create_directory(self.main_component_path)
            print('Creating `idf_component.yml` in the main component directory')
            shutil.copyfile(example_path, self.main_manifest_path)

    def pack_component(self, args):
        def _filter_files(info):
            # Ignore dist files
            if os.path.split(info.path)[-1] == 'dist':
                return None
            return info

        manifest = ManifestManager(self.path, args['name'], check_required_fields=True).load()
        archive_file = _archive_name(manifest)
        print('Saving archive to %s' % os.path.join(self.dist_path, archive_file))
        pack_archive(
            source_directory=self.path,
            destination_directory=self.dist_path,
            filename=archive_file,
            filter=_filter_files)

    def upload_component(self, args):
        client, namespace = service_details(args.get('namespace'), args.get('service_profile'))
        archive_file = args.get('archive')
        if archive_file:
            if not os.path.isfile(archive_file):
                raise FatalError('Cannot find archive to upload: {}'.format(archive_file))

            tempdir = tempfile.mkdtemp()
            try:
                unpack_archive(archive_file, tempdir)
                manifest = ManifestManager(tempdir, args['name'], check_required_fields=True).load()
            finally:
                shutil.rmtree(tempdir)

        else:
            manifest = ManifestManager(self.path, args['name'], check_required_fields=True).load()
            archive_file = os.path.join(self.dist_path, _archive_name(manifest))
            if not os.path.isfile(archive_file):
                self.pack_component(args)

        try:
            component_name = '/'.join([namespace, manifest.name])
            # Checking if current version already uploaded
            versions = client.versions(component_name, spec='*').versions
            if manifest.version in versions:
                raise NothingToDoError(
                    'Version {} of the component "{}" is already on the service'.format(
                        manifest.version, component_name))

            # Uploading the component
            print('Uploading archive: %s' % archive_file)
            client.upload_version(component_name=component_name, file_path=archive_file)
            print('Component was successfully uploaded')
        except APIClientError as e:
            raise FatalError(e)

    def create_remote_component(self, args):
        client, namespace = service_details(args.get('namespace'), args.get('service_profile'))
        name = '/'.join([namespace, args['name']])
        try:
            client.create_component(component_name=name)
            print('Component "%s" was successfully created' % name)
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
            and os.path.isfile(os.path.join(component['path'], 'idf_component.yml'))
        ]

        downloaded_component_paths = set()
        if local_components:
            downloaded_component_paths = download_project_dependencies(
                local_components, self.lock_path, self.managed_components_path)

        # Exclude requirements paths
        downloaded_component_paths -= {component['path'] for component in local_components}
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

        requirements_manager.dump(requirements)


def _archive_name(manifest):  # type (Manifest) -> str
    return '%s_%s.tgz' % (manifest.name, manifest.version)
