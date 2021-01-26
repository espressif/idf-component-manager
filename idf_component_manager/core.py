"""Core module of component manager"""
from __future__ import print_function

import os
from collections import namedtuple
from io import open
from shutil import copyfile
from typing import Union

from tqdm import tqdm

from idf_component_tools.api_client import APIClient, APIClientError
from idf_component_tools.archive_tools import pack_archive
from idf_component_tools.errors import FatalError, ManifestError
from idf_component_tools.file_tools import create_directory
from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import ComponentRequirement, Manifest, ManifestManager
from idf_component_tools.sources.fetcher import ComponentFetcher
from idf_component_tools.sources.local import LocalSource
from idf_component_tools.sources.web_service import default_component_service_url

from .config import ConfigManager
from .local_component_list import parse_component_list
from .version_solver.version_solver import VersionSolver

ServiceDetails = namedtuple('ServiceDetails', ['client', 'namespace'])


def _service_details(args):
    config = ConfigManager().load()
    profile_name = args.get('service_profile') or 'default'
    profile = config.profiles.get(profile_name, {})

    service_url = profile.get('url')
    if not service_url or service_url == 'default':
        service_url = default_component_service_url()

    # Priorities: idf.py option > IDF_COMPONENT_NAMESPACE env variable > profile value
    namespace = args.get('namespace') or profile.get('default_namespace')
    if not namespace:
        raise FatalError('Namespace is required to upload component')

    # Priorities: IDF_COMPONENT_API_TOKEN env variable > profile value
    token = os.getenv('IDF_COMPONENT_API_TOKEN', profile.get('api_token'))
    if not token:
        raise FatalError('API token is required to upload component')

    client = APIClient(base_url=service_url, auth_token=token)

    return ServiceDetails(client, namespace)


class ComponentManager(object):
    def __init__(self, path, lock_path=None, manifest_path=None, main_component_path=None):
        # type: (str, Union[None, str], Union[None, str], Union[None, str]) -> None

        # Working directory
        self.path = os.path.abspath(path if os.path.isdir(path) else os.path.dirname(path))

        # Set path of the project's main component
        self.main_component_path = main_component_path or os.path.join(self.path, 'main')

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
            print('`idf_component.yml` already exists in main component directroy, skipping...')
        else:
            example_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'templates', 'idf_component_template.yml')
            create_directory(self.main_component_path)
            print('Creating `idf_component.yml` in the main component directory')
            copyfile(example_path, self.main_manifest_path)

    def _component_manifest(self):
        manager = ManifestManager(os.path.join(self.path, 'idf_component.yml'))
        manifest = Manifest.fromdict(manager.load())

        if not (manifest.name or manifest.version):
            raise ManifestError('Component name and version have to be in the component manifest')

        return manifest

    def _archive_name(self, manifest):
        return '%s_%s.tgz' % (manifest.name, manifest.version)

    def pack_component(self, args):
        def _filter_files(info):
            # Ignore dist files
            if os.path.split(info.path)[-1] == 'dist':
                return None
            return info

        manifest = self._component_manifest()
        archive_file = self._archive_name(manifest)
        print('Saving archive to %s' % os.path.join(self.dist_path, archive_file))
        pack_archive(
            source_directory=self.path,
            destination_directory=self.dist_path,
            filename=archive_file,
            filter=_filter_files)

    def upload_component(self, args):
        client, namespace = _service_details(args)
        manifest = self._component_manifest()
        archive_file = os.path.join(self.dist_path, self._archive_name(manifest))
        print('Uploading archive: %s' % archive_file)

        try:
            client.upload_version(component_name='/'.join([namespace, manifest.name]), file_path=archive_file)
            print('Component was successfully uploaded')
        except APIClientError as e:
            raise FatalError(e)

    def create_remote_component(self, args):
        client, namespace = _service_details(args)
        name = '/'.join([namespace, args['name']])
        try:
            client.create_component(component_name=name)
            print('Component "%s" was successfully created' % name)
        except APIClientError as e:
            raise FatalError(e)

    def prepare_dep_dirs(self, managed_components_list_file, local_components_list_file=None):
        # Find all manifests
        if local_components_list_file and os.path.isfile(local_components_list_file):
            local_components = parse_component_list(local_components_list_file)
        else:
            components_items = os.listdir(self.components_path)
            local_components = [
                {
                    'name': item,
                    'path': os.path.join(self.components_path, item)
                } for item in components_items if os.path.isdir(os.path.join(self.components_path, item))
            ]
            local_components.append({'name': 'main', 'path': self.main_component_path})

        # Checking that CMakeLists.txt exists for all component dirs
        local_components = [
            component for component in local_components
            if os.path.isfile(os.path.join(component['path'], 'CMakeLists.txt'))
        ]

        project_requirements = [
            ComponentRequirement(
                name=component['name'], source=LocalSource(source_details={'path': component['path']}))
            for component in local_components
        ]

        manifest = Manifest(dependencies=project_requirements)
        lock_manager = LockManager(self.lock_path)
        solution = lock_manager.load()

        if manifest.manifest_hash != solution.manifest_hash:
            solver = VersionSolver(manifest, solution)
            print('Solving dependencies requirements')
            solution = solver.solve()

            print('Updating lock file at %s' % self.lock_path)
            lock_manager.dump(solution)

        # Download components
        downloaded_component_paths = set()

        if solution.dependencies:
            for component in tqdm(solution.dependencies):
                download_path = ComponentFetcher(component, self.managed_components_path).download()
                downloaded_component_paths.add(download_path)

        # Exclude requirements paths
        downloaded_component_paths -= {component['path'] for component in local_components}

        # Include managed components in project directory
        with open(managed_components_list_file, mode='w', encoding='utf-8') as file:
            for component_path in downloaded_component_paths:
                file.write(u'idf_build_component("%s")' % component_path)

    def inject_requirements(self, component_requires_file):
        pass
        # TODO: update requirements for known components
        # TODO: deal with namespaces

        # solution = self.install()
        # And update temporary requirements file
        # if solution.dependencies:
        #     with open(args.component_requires_file, mode='r', encoding='utf-8') as f:
        #         data = f.read()

        #     with open(args.component_requires_file, mode='w', encoding='utf-8') as f:
        #         for component in solution.dependencies:
        #             # TODO: deal with IDF as component-bundle
        #             if component.name == 'idf':
        #                 continue

        #             name_parts = component.name.split('/')
        #             f.write(
        #                 '\nidf_build_component("%s")' % os.path.join(args.project_dir,
        # "managed_components", *name_parts))

        #         f.write(data)
