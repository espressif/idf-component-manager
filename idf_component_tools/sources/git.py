# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import re
import shutil
import tempfile
import typing as t
from hashlib import sha256
from urllib.parse import urlparse  # type: ignore

from idf_component_tools.hash_tools.calculate import hash_dir

from ..errors import FetchingError
from ..file_tools import copy_filtered_directory
from ..git_client import GitClient
from ..manifest import (
    MANIFEST_FILENAME,
    ComponentVersion,
    ComponentWithVersions,
    HashedComponentVersion,
    ManifestManager,
)
from ..manifest.solved_component import SolvedComponent
from .base import BaseSource

BRANCH_TAG_RE = re.compile(
    r'^(?!.*/\.)(?!.*\.\.)(?!/)(?!.*//)(?!.*@\{)(?!.*\\)[^\177\s~^:?*\[]+[^.]$'
)


class GitSource(BaseSource):
    NAME = 'git'

    def __init__(self, source_details=None, **kwargs):
        super().__init__(source_details=source_details, **kwargs)
        self.git_repo = self.source_details['git']
        self.component_path = self.source_details.get('path') or '.'

        self._client = GitClient()

    def _checkout_git_source(
        self,
        version: t.Union[str, ComponentVersion, None],
        path: str,
        selected_paths: t.Optional[t.List[str]] = None,
    ) -> str:
        if version is not None:
            version = None if version == '*' else str(version)
        return self._client.prepare_ref(
            repo=self.git_repo,
            bare_path=self.cache_path(),
            checkout_path=path,
            ref=version,
            with_submodules=True,
            selected_paths=selected_paths,
        )

    @staticmethod
    def create_sources_if_valid(
        name: str, details: t.Dict, manifest_manager: t.Optional[ManifestManager] = None
    ) -> t.Optional[t.List[BaseSource]]:
        if details.get('git', None):
            return [GitSource(details, manifest_manager=manifest_manager)]
        return None

    @classmethod
    def required_keys(cls):
        return {'git': 'str'}

    @classmethod
    def optional_keys(cls):
        return {'path': 'str'}

    @property
    def component_hash_required(self) -> bool:
        return True

    @property
    def downloadable(self) -> bool:
        return True

    @property
    def hash_key(self):
        if self._hash_key is None:
            url = urlparse(self.git_repo)
            netloc = url.netloc
            path = '/'.join(filter(None, url.path.split('/')))
            normalized_path = '/'.join([netloc, path])
            self._hash_key = sha256(normalized_path.encode('utf-8')).hexdigest()
        return self._hash_key

    @property
    def volatile(self) -> bool:
        return True

    def cache_path(self):
        # Using `b_` prefix for bare git repos in cache
        path = os.path.join(self.system_cache_path, f'b_{self.NAME}_{self.hash_key[:8]}')
        return path

    def download(self, component: SolvedComponent, download_path: str) -> t.Optional[str]:
        # Check for required components
        if not component.component_hash:
            raise FetchingError('Component hash is required for components from git repositories')

        if not component.version:
            raise FetchingError(f'Version should provided for {component.name}')

        if self.up_to_date(component, download_path):
            return download_path

        temp_dir = tempfile.mkdtemp()
        try:
            self._checkout_git_source(
                component.version, temp_dir, selected_paths=[self.component_path]
            )
            source_path = os.path.join(str(temp_dir), self.component_path)
            if not os.path.isdir(source_path):
                raise FetchingError(
                    'Directory {} wasn\'t found for the commit id "{}" of the '
                    'git repository "{}"'.format(
                        self.component_path, component.version, self.git_repo
                    )
                )

            if os.path.isdir(download_path):
                shutil.rmtree(download_path)

            possible_manifest_filepath = os.path.join(source_path, MANIFEST_FILENAME)
            include, exclude = set(), set()
            if os.path.isfile(possible_manifest_filepath):
                manifest = ManifestManager(possible_manifest_filepath, component.name).load()
                include.update(manifest.files['include'])
                exclude.update(manifest.files['exclude'])

            copy_filtered_directory(source_path, download_path, include=include, exclude=exclude)
        finally:
            shutil.rmtree(temp_dir)

        return download_path

    def versions(self, name, details=None, spec='*', target=None):
        """For git returns hash of locked commit, ignoring manifest"""
        version = None if spec == '*' else spec
        temp_dir = tempfile.mkdtemp()
        try:
            commit_id = self._checkout_git_source(
                version, temp_dir, selected_paths=[self.component_path]
            )
            source_path = os.path.join(str(temp_dir), self.component_path)

            if not os.path.isdir(source_path):
                dependency_description = f'commit id "{commit_id}"'
                if version:
                    dependency_description = 'version "{}" ({})'.format(
                        version, dependency_description
                    )
                raise FetchingError(
                    'Directory {} wasn\'t found for the {} of the git repository "{}"'.format(
                        self.component_path, dependency_description, self.git_repo
                    )
                )

            manifest_path = os.path.join(source_path, MANIFEST_FILENAME)
            targets = []
            dependencies = []
            include = set()
            exclude = set()

            if os.path.isfile(manifest_path):
                manifest = ManifestManager(manifest_path, name=name).load()
                dependencies = manifest.dependencies

                if manifest.targets:  # only check when exists
                    if target and target not in manifest.targets:
                        raise FetchingError(
                            'Version "{}" (commit id "{}") of the component "{}" '
                            'does not support target "{}"'.format(version, commit_id, name, target)
                        )

                    targets = manifest.targets

                    include = set(manifest.files['include'])
                    exclude = set(manifest.files['exclude'])

            component_hash = hash_dir(source_path, include=include, exclude=exclude)
        finally:
            shutil.rmtree(temp_dir)

        return ComponentWithVersions(
            name=name,
            versions=[
                HashedComponentVersion(
                    commit_id,
                    targets=targets,
                    component_hash=component_hash,
                    dependencies=dependencies,
                )
            ],
        )

    def serialize(self) -> t.Dict:
        source = {
            'git': self.git_repo,
            'type': self.name,
        }

        if self.component_path:
            source['path'] = self.component_path

        return source

    def validate_version_spec(self, spec: str) -> bool:
        if not spec or spec == '*':
            return True

        return bool(BRANCH_TAG_RE.match(spec))

    def normalize_spec(self, spec: str) -> str:
        if not spec:
            return '*'
        ref = None if spec == '*' else spec
        commit_id = self._client.get_commit_id_by_ref(self.git_repo, self.cache_path(), ref)
        return commit_id
