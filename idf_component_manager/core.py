"""Core module of component manager"""
from __future__ import print_function

import os
from collections import namedtuple
from io import open
from shutil import copyfile
from typing import Union

from idf_component_tools.api_client import APIClient, APIClientError
from idf_component_tools.archive_tools import pack_archive
from idf_component_tools.errors import FatalError, ManifestError
from idf_component_tools.file_tools import create_directory
from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import Manifest, ManifestManager, SolvedManifest
from idf_component_tools.sources.fetcher import ComponentFetcher
from idf_component_tools.sources.web_service import default_component_service_url

from .config import ConfigManager
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
        self.path = path if os.path.isdir(path) else os.path.dirname(path)

        # Set path of the project's main component
        self.main_component_path = main_component_path or os.path.join(self.path, 'main')

        # Set path of the manifest file for the project's main component
        self.main_manifest_path = manifest_path or (
            os.path.join(path, 'main', 'idf_component.yml') if os.path.isdir(path) else path)

        # Lock path
        self.lock_path = lock_path or (os.path.join(path, 'dependencies.lock') if os.path.isdir(path) else path)

        # Components directory
        self.components_path = os.path.join(self.path, 'managed_components')

        # Dist directory
        self.dist_path = os.path.join(self.path, 'dist')

    def init_project(self, args):
        """Create manifest file if it doesn't exist in work directory"""
        if os.path.exists(self.main_manifest_path):
            print('`idf_component.yml` already exists in main component directroy, skipping...')
        else:
            example_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'templates', 'idf_component_template.yml')
            create_directory(self.main_component_path)
            print('Creating `idf_component.yml` in the main component directory')
            copyfile(example_path, self.main_manifest_path)

    def install(self, args):
        manager = ManifestManager(self.main_manifest_path)
        manifest = Manifest.from_dict(manager.load())
        lock_manager = LockManager(self.lock_path)
        lock = lock_manager.load()
        solution = SolvedManifest.from_dict(manifest, lock)

        if manifest.manifest_hash != lock['manifest_hash']:
            solver = VersionSolver(manifest, lock)
            solution = solver.solve()

            # Create lock only if manifest exists
            if manager.exists():
                print('Updating lock file at %s' % self.lock_path)
                lock_manager.dump(solution)

        # Download components
        if not solution.solved_components:
            return solution

        components_count = len(solution.solved_components)
        count_string = 'dependencies' if components_count != 1 else 'dependency'
        print('Processing %s %s' % (components_count, count_string))
        for i, component in enumerate(solution.solved_components):
            print('[%d/%d] Processing component %s' % (i + 1, components_count, component.name))
            ComponentFetcher(component, self.components_path).download()

        print('Successfully processed %s %s ' % (components_count, count_string))
        return solution

    def _component_manifest(self):
        manager = ManifestManager(os.path.join(self.path, 'idf_component.yml'))
        manifest = Manifest.from_dict(manager.load())

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

        # Process them all

        # Install dependencies first
        solution = self.install({})

        # Include managed components in project directory
        with open(managed_components_list_file, mode='w', encoding='utf-8') as f:
            # Use idf_build_component for all components
            if solution.solved_components:
                f.write(u'idf_build_component("%s")' % self.components_path)

    def inject_requirements(self, component_requires_file):
        pass
        # TODO: update requirements for known components
        # TODO: deal with namespaces

        # solution = self.install()
        # And update temporary requirements file
        # if solution.solved_components:
        #     with open(args.component_requires_file, mode='r', encoding='utf-8') as f:
        #         data = f.read()

        #     with open(args.component_requires_file, mode='w', encoding='utf-8') as f:
        #         for component in solution.solved_components:
        #             # TODO: deal with IDF as component-bundle
        #             if component.name == 'idf':
        #                 continue

        #             name_parts = component.name.split('/')
        #             f.write(
        #                 '\nidf_build_component("%s")' % os.path.join(args.project_dir,
        # "managed_components", *name_parts))

        #         f.write(data)
