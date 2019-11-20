import os
import re
import subprocess  # nosec
from typing import List, Union

from semantic_version import Version

from component_manager.utils.errors import FatalError


# Git error that is suppossed to be handled in the code, non-fatal
class GitCommandError(Exception):
    pass


# Non-recoverable error
class GitFatalError(Exception):
    pass


class GitClient(object):
    """ Set of tools for working with git repos """
    def __init__(self, git_command='git'):  # type: (str) -> None
        self.git_command = git_command or 'git'

    def is_git_dir(self, path):
        try:
            return self.run(['rev-parse', '--is-inside-work-tree'], cwd=path).strip() == 'true'
        except GitCommandError:
            return False

    def prepare_branch(self, repo, path, branch=None, with_submodules=True):
        """
        Checkout required branch to desired path. Clones a repo, if necessary
        """

        # Check if target dir is already a valid repo
        if self.is_git_dir(path):
            self.run(['fetch', 'origin'], cwd=path)
        else:
            # Init empty repo
            self.run(['init', '.'], cwd=path)
            # Add remote
            self.run(['remote', 'add', 'origin', repo], cwd=path)
            # And fetch
            self.run(['fetch', 'origin'], cwd=path)

        if branch:
            # If branch is provided check that exists
            try:
                self.run(['cat-file', '-t', branch])
            except GitCommandError:
                FatalError('Error: branch "%s" doesn\'t exist in repo "%s"' % (branch, repo))

        else:
            # Set to latest commit from remote's head
            branch = self.run(['ls-remote', '--exit-code', 'origin', 'HEAD'])[:40]

        # Checkout required branch
        self.run(['checkout', '--force', branch], cwd=path)
        # And remove all untracked files
        self.run(['reset', '--hard'], cwd=path)

        # Submodules
        if with_submodules:
            self.run(['submodule', 'update', '--init', '--recursive'], cwd=path)

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
            raise GitCommandError("'git %s' failed with exit code %d \n%s" %
                                  (' '.join(args), e.returncode, e.output.decode('utf-8')))

    def check_version(
            self,
            min_supported='2.13.0',  # As for Aug 2019 2.13 is the oldest supported version of git
    ):  # type: (Union[str,Version]) -> bool
        try:
            version = self.version()
            min_supported = min_supported if isinstance(min_supported, Version) else Version(min_supported)

            if version < min_supported:
                raise GitFatalError('Your git version %s is older than minimally required %s.' % (
                    version,
                    min_supported,
                ))

        except GitCommandError:
            raise GitFatalError("git command wasn't found")

        return True

    def version(self):  # type: () -> Version
        ver_match = re.match(r"^git version (.*)$", self.run(['--version']))

        try:
            if ver_match:
                return Version(ver_match.group(1))
            else:
                raise GitCommandError()
        except (IndexError, ValueError, GitCommandError):
            raise GitFatalError('Cannot recognize git version')
