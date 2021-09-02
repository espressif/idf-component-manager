import os
import re
import subprocess  # nosec

from semantic_version import Version

from .errors import GitError

try:
    from typing import List, Union
except ImportError:
    pass


# Git error that is supposed to be handled in the code, non-fatal
class GitCommandError(Exception):
    pass


class GitClient(object):
    """ Set of tools for working with git repos """
    def __init__(self, git_command='git'):  # type: (str) -> None
        self.git_command = git_command or 'git'

    def commit_id(self, path):  # type: (str) -> str
        return self.run(['show', '--format="%H"', '--no-patch'], cwd=path)

    def is_dirty(self, path):  # type: (str) -> bool
        try:
            self.run(['diff', '--quiet'], cwd=path)
            return False
        except GitCommandError:
            return True

    def is_git_dir(self, path):  # type: (str) -> bool
        try:
            return self.run(['rev-parse', '--is-inside-work-tree'], cwd=path).strip() == 'true'
        except GitCommandError:
            return False

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

        return self.run(['rev-parse', '--verify', 'HEAD'], cwd=path)

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

    def check_version(self, min_supported='2.0.0'):  # type: (Union[str,Version]) -> bool
        try:
            version = self.version()
            min_supported = min_supported if isinstance(min_supported, Version) else Version(min_supported)

            if version < min_supported:
                raise GitError('Your git version %s is older than minimally required %s.' % (
                    version,
                    min_supported,
                ))

        except GitCommandError:
            raise GitError("git command wasn't found")

        return True

    def version(self):  # type: () -> Version
        ver_match = re.match(r'^git version (\d+\.\d+\.\d+)', self.run(['--version']))

        try:
            if ver_match:
                return Version(ver_match.group(1))
            else:
                raise GitCommandError()
        except (IndexError, ValueError, GitCommandError):
            raise GitError('Cannot recognize git version')
