import os
import shutil
from hashlib import sha256

from ..file_cache import FileCache
from ..file_tools import create_directory
from ..git_client import GitClient
from ..hash_tools import validate_dir
from ..manifest import ComponentVersion, ComponentWithVersions, HashedComponentVersion
from .base import BaseSource

try:
    from urllib.parse import urlparse  # type: ignore
except ImportError:
    from urlparse import urlparse  # type: ignore

try:
    from typing import Dict, Union
except ImportError:
    pass


class GitSource(BaseSource):
    NAME = 'git'

    def __init__(self, source_details=None):
        super(GitSource, self).__init__(source_details=source_details)
        self.git_repo = source_details['git']
        self.component_path = source_details.get('path', '')
        self.cache_path = os.path.join(FileCache.path(), 'git~%s' % self.hash_key)
        create_directory(self.cache_path)
        self._client = GitClient()
        # Check for git client immediately
        self._client.check_version()

    def _checkout_git_source(self, version):  # type: (Union[str, ComponentVersion, None]) -> None
        if version is not None:
            version = str(version)

        return self._client.prepare_ref(repo=self.git_repo, path=self.cache_path, ref=version, with_submodules=True)

    @staticmethod
    def is_me(name, details):  # type: (str, dict) -> bool
        return bool(details.get('git', None))

    @classmethod
    def required_keys(cls):
        return ['git']

    @classmethod
    def optional_keys(cls):
        return ['path']

    @property
    def downloadable(self):  # type: () -> bool
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

    def download(self, component, download_path):
        dest_path = os.path.join(download_path)
        component_hash = component.component_hash

        if component_hash and validate_dir(dest_path, component_hash):
            return dest_path

        self._checkout_git_source(component.version)
        source_path = os.path.join(self.cache_path, self.component_path)

        if os.path.isdir(dest_path):
            shutil.rmtree(dest_path)
        shutil.copytree(source_path, dest_path)
        return [dest_path]

    def versions(self, name, details=None, spec='*'):
        """For git returns hash of locked commit, ignoring manifest"""
        version = None if spec == '*' else spec
        commit_id = self._checkout_git_source(version)
        return ComponentWithVersions(name=name, versions=[HashedComponentVersion(commit_id)])

    def serialize(self):  # type: () -> Dict
        source = {
            'git': self.git_repo,
            'type': self.name,
        }

        if self.component_path:
            source['path'] = self.component_path

        return source
