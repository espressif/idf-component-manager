import os
import shutil
from collections import OrderedDict
from hashlib import sha256
from typing import Union

from component_management_tools.hash_tools import validate_dir

from ..manifest import ComponentVersion, ComponentWithVersions
from ..utils.file_cache import FileCache
from ..utils.file_tools import create_directory
from ..utils.git_client import GitClient
from .base import BaseSource

try:
    from urllib.parse import urlparse  # type: ignore
except ImportError:
    from urlparse import urlparse  # type: ignore


class GitSource(BaseSource):
    def __init__(self, source_details=None):
        super(GitSource, self).__init__(source_details=source_details)
        self.git_repo = source_details['git']
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

    @staticmethod
    def known_keys():
        """List of known details key"""
        return ['version', 'path', 'git']

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
        source_path = os.path.join(self.cache_path, component.source_specific_options.get('path', ''))

        if os.path.isdir(dest_path):
            shutil.rmtree(dest_path)
        # TODO: fix ignore function
        # ignore = copytree_ignore()
        shutil.copytree(source_path, dest_path)
        return dest_path

    def versions(self, name, details=None, spec='*'):
        """For git returns hash of locked commit, ignoring manifest"""
        version = None if spec == '*' else spec
        commit_id = self._checkout_git_source(version)
        return ComponentWithVersions(name=name, versions=[ComponentVersion(commit_id)])

    def as_ordered_dict(self):  # type: () -> OrderedDict
        return OrderedDict([('git', self.git_repo), ('type', self.name)])
