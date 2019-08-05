import os
import shutil
from collections import OrderedDict
from hashlib import sha256

from component_manager import ComponentVersion, ComponentWithVersions
from component_manager.utils.file_cache import FileCache
from component_manager.utils.file_tools import copytree_ignore
from component_manager.utils.git_client import GitClient, GitCommandError
from component_manager.utils.hash_tools import validate_dir

from .base import BaseSource
from .errors import FetchingError

try:
    from urllib.parse import urlparse  # type: ignore
except ImportError:
    from urlparse import urlparse  # type: ignore


class GitSource(BaseSource):
    def __init__(self, source_details=None):
        super(GitSource, self).__init__(source_details=source_details)

        self.git_repo = source_details['git']
        self.cache_path = os.path.join(FileCache.path(), 'git~%s' % self.hash_key)
        self._client = GitClient()
        # Check for git client immediately
        self._client.check_version()

    def _checkout_git_source(self, details):
        try:
            self._client.prepare_branch(
                repo=self.git_repo,
                path=self.cache_path,
                branch=details.get('version'),
                with_submodules=True,
            )
        except GitCommandError:
            raise FetchingError('Cannot clone repo: %s' % self.git_repo)

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

    def download(self, name, details, download_path):
        dest_path = os.path.join(download_path, name)

        component_hash = details.get('component_hash')
        # TODO: what if not? Add validation for required details...
        if component_hash and validate_dir(dest_path, component_hash):
            return dest_path

        self._checkout_git_source(details)
        source_path = os.path.join(self.cache_path, details.get('path', ''))
        shutil.copytree(source_path, dest_path, ignore=copytree_ignore())

        return dest_path

    def versions(self, name, details, spec='*'):
        """For git returns hash of locked commit, ignoring manifest"""
        self._checkout_git_source(details)

        commit_id = self._client.run(['rev-parse', '--verify', 'head'])
        return ComponentWithVersions(name=name, versions=[ComponentVersion(commit_id)])

    def as_ordered_dict(self):  # type: () -> OrderedDict
        return OrderedDict([('git', self.git_repo), ('type', self.name)])
