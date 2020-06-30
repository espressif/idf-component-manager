"""Core module of component manager"""
from __future__ import print_function

import os
from io import open
from shutil import copyfile
from typing import Union

from idf_component_tools.api_client import APIClient, APIClientError
from idf_component_tools.archive_tools import pack_archive
from idf_component_tools.errors import FatalError, ManifestError
from idf_component_tools.lock import LockManager
from idf_component_tools.manifest import Manifest, ManifestManager, SolvedManifest
from idf_component_tools.sources.fetcher import ComponentFetcher
from idf_component_tools.sources.web_service import default_component_service_url

from .config import ConfigManager
from .version_solver.version_solver import VersionSolver


class ComponentManager(object):
    def __init__(self, path, lock_path=None, manifest_path=None):
        # type: (str, Union[None, str], Union[None, str]) -> None

        # Working directory
        self.path = path if os.path.isdir(path) else os.path.dirname(path)

        # Set path of manifest file for the project
        self.project_manifest_path = manifest_path or (
            os.path.join(path, 'idf_project.yml') if os.path.isdir(path) else path)

        # Lock path
        self.lock_path = lock_path or (os.path.join(path, 'dependencies.lock') if os.path.isdir(path) else path)

        # Components directory
        self.components_path = os.path.join(self.path, 'managed_components')

        # Dist directory
        self.dist_path = os.path.join(self.path, 'dist')

    def init_project(self, args):
        """Create manifest file if it doesn't exist in work directory"""
        if os.path.exists(self.project_manifest_path):
            print('`idf_project.yml` already exists in projects folder, skipping...')
        else:
            example_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'templates', 'idf_project_template.yml')
            print('Creating `idf_project.yml` in projects folder')
            copyfile(example_path, self.project_manifest_path)

    def install(self, args):
        manager = ManifestManager(self.project_manifest_path)
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
            line = ('[%d/%d] Processing component %s' % (i + 1, components_count, component.name))
            print(line)
            ComponentFetcher(component, self.components_path).download()

        print('Successfully processed %s %s ' % (components_count, count_string))
        return solution

    def _component_manifest(self):
        manager = ManifestManager(os.path.join(self.path, 'idf_component.yml'), is_component=True)
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
        config = ConfigManager().load()

        profile_name = args.get('service_profile', 'default')
        profile = config.profiles.get(profile_name, {})
        service_url = profile.get('url')
        if not service_url or service_url == 'default':
            service_url = default_component_service_url()

        manifest = self._component_manifest()
        archive_file = os.path.join(self.dist_path, self._archive_name(manifest))
        print('Uploading archive: %s' % archive_file)

        # Priorities: idf.py option > IDF_COMPONENT_NAMESPACE env variable > profile value
        namespace = args.get('namespace', profile.get('default_namespace'))

        if not namespace:
            raise FatalError('Namespace is required to upload component')

        # Priorities: IDF_COMPONENT_API_TOKEN env variable > profile value
        token = os.getenv('IDF_COMPONENT_API_TOKEN', profile.get('api_token'))

        if not token:
            raise FatalError('API token is required to upload component')

        client = APIClient(base_url=service_url, auth_token=token)

        try:
            client.upload_version(component_name='/'.join([namespace, manifest.name]), file_path=archive_file)
        except APIClientError as e:
            raise FatalError(e)

        print('Component was successfully uploaded')

    def prepare_dep_dirs(self, managed_components_list_file):
        # Install dependencies first
        solution = self.install({})

        # Include managed components in project directory
        with open(managed_components_list_file, mode='w', encoding='utf-8') as f:
            # TODO: write all components individually
            if solution.solved_components:
                f.write(u'__project_component_dir("%s")' % self.components_path)

    def inject_requrements(self, component_requires_file):
        pass
        # TODO: update requirements for known components
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
