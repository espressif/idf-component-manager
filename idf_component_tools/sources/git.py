# SPDX-FileCopyrightText: 2022-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import posixpath
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
from idf_component_tools.messages import warn
from idf_component_tools.utils import (
    ComponentVersion,
    ComponentWithVersions,
    HashedComponentVersion,
    subst_vars_in_str,
)

from .base import BaseSource

if t.TYPE_CHECKING:
    from idf_component_tools.manifest import ComponentRequirement, SolvedComponent

BRANCH_TAG_RE = re.compile(
    r'^(?!.*/\.)(?!.*\.\.)(?!/)(?!.*//)(?!.*@\{)(?!.*\\)[^\177\s~^:?*\[]+[^.]$'
)


class GitSource(BaseSource):
    type: t.Literal['git'] = 'git'  # type: ignore
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

        # Repo-root git deps use path "." — basename(".") is not a component directory.
        # Compare the install dir (what CMake sees) instead.
        directory_name = posixpath.basename(posixpath.normpath(self.repo_path))
        if directory_name == '.':
            directory_name = os.path.basename(os.path.normpath(download_path))
        if directory_name:
            self._warn_if_component_name_mismatch(component.name, directory_name)

        temp_dir = tempfile.mkdtemp()
        try:
            self._checkout_git_source(component.version, temp_dir, selected_paths=[self.repo_path])
            source_path = os.path.join(str(temp_dir), self.repo_path)
            if not os.path.isdir(source_path):
                raise FetchingError(
                    'Directory {} was not found for the commit id "{}" of the '
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

    def _resolve_local_paths(
        self,
        dependencies: t.List['ComponentRequirement'],
        commit_id: str,
    ) -> t.List['ComponentRequirement']:
        """Transform local dependencies into git dependencies within the same repository.

        Relative path and override_path dependencies in a git-fetched component refer to
        other components in that repository. Resolving them as git dependencies keeps the
        lock file portable after the temporary checkout is removed.
        """
        resolved = []
        for dep in dependencies:
            local_paths = []
            if dep.override_path:
                local_paths.append(('override_path', dep.override_path))
            if dep.path and not dep.git:
                local_paths.append(('path', dep.path))

            if not local_paths:
                resolved.append(dep)
                continue

            repo_relative_path = None
            for field_name, local_path in local_paths:
                local_path = subst_vars_in_str(local_path)
                candidate_path = posixpath.normpath(posixpath.join(self.repo_path, local_path))

                virtual_repo_root = '/__idf_component_repo__'
                resolved_abs = posixpath.normpath(posixpath.join(virtual_repo_root, candidate_path))

                if resolved_abs == virtual_repo_root or resolved_abs.startswith(
                    virtual_repo_root + '/'
                ):
                    if field_name == 'override_path' and dep.path:
                        warn(
                            'Both "path" and "override_path" are set for dependency "{}". '
                            'Using "override_path" relative to the parent Git repository "{}".'.format(
                                dep.name,
                                self.repo,
                            )
                        )
                    repo_relative_path = candidate_path
                    break

                if field_name == 'override_path':
                    warn(
                        'Ignoring override_path "{}" for dependency "{}": '
                        'path leads outside the git repository "{}". '
                        'The override will be ignored.'.format(
                            dep.override_path,
                            dep.name,
                            self.repo,
                        )
                    )
                    continue

                raise FetchingError(
                    'The "path" field for dependency "{}" in git component "{}" '
                    'points outside the git repository "{}": "{}".'.format(
                        dep.name,
                        self.repo_path,
                        self.repo,
                        dep.path,
                    )
                )

            if repo_relative_path is None:
                new_dep = dep.model_copy(update={'override_path': None})
                new_dep._source = None
                resolved.append(new_dep)
                continue

            new_dep = dep.model_copy(
                update={
                    'override_path': None,
                    'version': commit_id,
                    'git': self.git,
                    'path': repo_relative_path,
                }
            )
            new_dep._source = None
            resolved.append(new_dep)
        return resolved

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
                    'Directory {} was not found for the {} of the git repository "{}"'.format(
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
                dependencies = self._resolve_local_paths(dependencies, commit_id)
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
