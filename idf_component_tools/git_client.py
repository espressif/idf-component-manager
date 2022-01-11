import os
import re
import subprocess  # nosec
from functools import wraps

from semantic_version import Version

from .errors import GitError

try:
    from typing import Any, Callable, List, Optional, Union
except ImportError:
    pass


# Git error that is supposed to be handled in the code, non-fatal
class GitCommandError(Exception):
    pass


class GitClient(object):
    """ Set of tools for working with git repos """
    def __init__(self, git_command='git', min_supported='2.0.0'):  # type: (str, Union[str, Version]) -> None
        self.git_command = git_command or 'git'
        self.git_min_supported = min_supported if isinstance(min_supported, Version) else Version(min_supported)

        self._git_checked = False

    def _git_cmd(func):  # type: (Union[GitClient, Callable[..., Any]]) -> Callable
        @wraps(func)  # type: ignore
        def wrapper(self, *args, **kwargs):
            if not self._git_checked:
                self.check_version()
                self._git_checked = True

            return func(self, *args, **kwargs)

        return wrapper

    @_git_cmd
    def commit_id(self, path):  # type: (str) -> str
        return self.run(['show', '--format="%H"', '--no-patch'], cwd=path)

    @_git_cmd
    def is_dirty(self, path):  # type: (str) -> bool
        try:
            self.run(['diff', '--quiet'], cwd=path)
            return False
        except GitCommandError:
            return True

    @_git_cmd
    def is_git_dir(self, path):  # type: (str) -> bool
        try:
            return self.run(['rev-parse', '--is-inside-work-tree'], cwd=path).strip() == 'true'
        except GitCommandError:
            return False

    @_git_cmd
    def prepare_ref(self, repo, path, ref=None, with_submodules=True):
        """
        Checkout required branch to desired path. Clones a repo, if necessary
        """
        if not os.path.exists(path):
            os.mkdir(path)

        # Check if target dir is already a valid repo
        if self.is_git_dir(path):
            # Check if it's up to date
            try:
                if ref and self.commit_id(path) == ref and not self.is_dirty(path):
                    return ref
            except GitCommandError:
                pass

            self.run(['fetch', 'origin'], cwd=path)
        else:
            # Init empty repo
            self.run(['init', '.'], cwd=path)
            # Add remote
            self.run(['remote', 'add', 'origin', repo], cwd=path)
            # And fetch
            self.run(['fetch', 'origin'], cwd=path)

        if ref:
            # If branch is provided check that exists
            try:
                self.run(['cat-file', '-t', ref])
            except GitCommandError:
                GitError('branch "%s" doesn\'t exist in repo "%s"' % (ref, repo))

        else:
            # Set to latest commit from remote's HEAD
            ref = self.run(['ls-remote', '--exit-code', 'origin', 'HEAD'], cwd=path)[:40]

        # Checkout required branch
        self.run(['checkout', '--force', ref], cwd=path)
        # And remove all untracked files
        self.run(['reset', '--hard'], cwd=path)

        # Submodules
        if with_submodules:
            self.run(['submodule', 'update', '--init', '--recursive'], cwd=path)

        return self.run(['rev-parse', '--verify', 'HEAD'], cwd=path).strip()

    def run(self, args, cwd=None):  # type: (List[str], str) -> str
        if cwd is None:
            cwd = os.getcwd()

        try:
            return subprocess.check_output(  # nosec
                [self.git_command] + list(args),
                cwd=cwd,
                stderr=subprocess.STDOUT,
            ).decode('utf-8')
        except subprocess.CalledProcessError as e:
            raise GitCommandError(
                "'git %s' failed with exit code %d \n%s" % (' '.join(args), e.returncode, e.output.decode('utf-8')))

    def check_version(self):  # type: () -> None
        version = self.version()

        if version < self.git_min_supported:
            raise GitError(
                'Your git version %s is older than minimally required %s.' % (
                    version,
                    self.git_min_supported,
                ))

    def version(self):  # type: () -> Version
        try:
            git_version_str = subprocess.check_output(  # nosec
                [self.git_command, '--version'],
                stderr=subprocess.STDOUT
            ).decode('utf-8')
        except OSError:
            raise GitError("git command wasn't found")

        ver_match = re.match(r'^git version (\d+\.\d+\.\d+)', git_version_str)

        try:
            if ver_match:
                return Version(ver_match.group(1))
            else:
                raise GitCommandError()
        except (IndexError, ValueError, GitCommandError):
            raise GitError('Cannot recognize git version')

    @_git_cmd
    def get_tag_version(self):  # type: () -> Optional[Version]
        try:
            tag_str = self.run(['describe', '--exact-match'])
            if tag_str.startswith('v'):
                tag_str = tag_str[1:]
        except GitCommandError:
            return None

        try:
            semantic_version = Version(tag_str)
            return semantic_version
        except ValueError:
            return None
