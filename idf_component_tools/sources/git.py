# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import re
import shutil
import tempfile
import typing as t

from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.errors import FetchingError
from idf_component_tools.file_tools import copy_filtered_directory
from idf_component_tools.git_client import GitClient
from idf_component_tools.hash_tools.calculate import hash_dir, hash_url
from idf_component_tools.hash_tools.checksums import ChecksumsModel
from idf_component_tools.manager import ManifestManager
from idf_component_tools.utils import (
    ComponentVersion,
    ComponentWithVersions,
    HashedComponentVersion,
    Literal,
    subst_vars_in_str,
)

from .base import BaseSource

if t.TYPE_CHECKING:
    from idf_component_tools.manifest import SolvedComponent

BRANCH_TAG_RE = re.compile(
    r'^(?!.*/\.)(?!.*\.\.)(?!/)(?!.*//)(?!.*@\{)(?!.*\\)[^\177\s~^:?*\[]+[^.]$'
)


class GitSource(BaseSource):
    type: Literal['git'] = 'git'  # type: ignore
    git: str
    path: str = '.'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._client = GitClient()

    def __repr__(self) -> str:
        return f'{self.type}({self.repo if self.path == "." else os.path.join(self.repo, self.repo_path)})'

    @property
    def repo(self) -> str:
        return subst_vars_in_str(self.git)

    @property
    def repo_path(self) -> str:
        return subst_vars_in_str(self.path)

    def _checkout_git_source(
        self,
        version: t.Union[str, ComponentVersion, None],
        path: str,
        selected_paths: t.Optional[t.List[str]] = None,
    ) -> str:
        if version is not None:
            version = None if version == '*' else str(version)
        return self._client.prepare_ref(
            repo=self.repo,
            bare_path=self.cache_path(),
            checkout_path=path,
            ref=version,
            with_submodules=True,
            selected_paths=selected_paths,
        )

    @property
    def downloadable(self) -> bool:
        return True

    @property
    def hash_key(self):
        if self._hash_key is None:
            self._hash_key = hash_url(self.repo)
        return self._hash_key

    @property
    def volatile(self) -> bool:
        return True

    def cache_path(self):
        # Using `b_` prefix for bare git repos in cache
        path = os.path.join(self.system_cache_path, 'b_{}_{}'.format(self.type, self.hash_key[:8]))
        return path

    def download(self, component: 'SolvedComponent', download_path: str) -> t.Optional[str]:
        # Check for required components
        if not component.component_hash:
            raise FetchingError('Component hash is required for components from git repositories')

        if not component.version:
            raise FetchingError(f'Version should provided for {component.name}')

        temp_dir = tempfile.mkdtemp()
        try:
            self._checkout_git_source(component.version, temp_dir, selected_paths=[self.repo_path])
            source_path = os.path.join(str(temp_dir), self.repo_path)
            if not os.path.isdir(source_path):
                raise FetchingError(
                    'Directory {} wasn\'t found for the commit id "{}" of the '
                    'git repository "{}"'.format(self.repo_path, component.version, self.repo)
                )

            if os.path.isdir(download_path):
                shutil.rmtree(download_path)

            possible_manifest_filepath = os.path.join(source_path, MANIFEST_FILENAME)
            include, exclude = set(), set()
            use_gitignore = False
            if os.path.isfile(possible_manifest_filepath):
                manifest = ManifestManager(possible_manifest_filepath, component.name).load()
                include.update(manifest.include_set)
                exclude.update(manifest.exclude_set)
                use_gitignore = manifest.use_gitignore

            copy_filtered_directory(
                source_path,
                download_path,
                use_gitignore=use_gitignore,
                include=include,
                exclude=exclude,
            )
        finally:
            shutil.rmtree(temp_dir)

        return download_path

    def versions(self, name, spec='*', target=None):
        """For git returns hash of locked commit, ignoring manifest"""
        version = None if spec == '*' else spec
        temp_dir = tempfile.mkdtemp()
        try:
            commit_id = self._checkout_git_source(
                version, temp_dir, selected_paths=[self.repo_path]
            )
            source_path = os.path.join(str(temp_dir), self.repo_path)

            if not os.path.isdir(source_path):
                dependency_description = f'commit id "{commit_id}"'
                if version:
                    dependency_description = 'version "{}" ({})'.format(
                        version, dependency_description
                    )
                raise FetchingError(
                    'Directory {} wasn\'t found for the {} of the git repository "{}"'.format(
                        self.repo_path, dependency_description, self.repo
                    )
                )

            manifest_path = os.path.join(source_path, MANIFEST_FILENAME)
            targets = []
            dependencies = []
            include = set()
            exclude = set()
            use_gitignore = False

            if os.path.isfile(manifest_path):
                manifest = ManifestManager(manifest_path, name=name).load()
                dependencies = manifest.raw_requirements
                use_gitignore = manifest.use_gitignore

                if manifest.targets:  # only check when exists
                    if target and target not in manifest.targets:
                        raise FetchingError(
                            'Version "{}" (commit id "{}") of the component "{}" '
                            'does not support target "{}"'.format(version, commit_id, name, target)
                        )

                    targets = manifest.targets

                include = manifest.include_set
                exclude = manifest.exclude_set

            component_hash = hash_dir(
                source_path, use_gitignore=use_gitignore, include=include, exclude=exclude
            )
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

    def validate_version_spec(self, spec: str) -> bool:
        if not spec or spec == '*':
            return True

        return bool(BRANCH_TAG_RE.match(spec))

    def normalize_spec(self, spec: str) -> str:
        if not spec:
            return '*'
        ref = None if spec == '*' else spec
        commit_id = self._client.get_commit_id_by_ref(self.repo, self.cache_path(), ref)
        return commit_id

    def exists(self, ref: t.Optional[str] = None) -> None:
        self._client.repo_exists(self.repo)
        self._client.ref_and_path_exists(
            repo=self.repo, bare_path=self.cache_path(), path=self.repo_path, ref=ref
        )

    def version_checksums(self, component: 'SolvedComponent') -> t.Optional[ChecksumsModel]:  # noqa: ARG002
        return None
