import os
import re
import subprocess  # nosec
from typing import List, Union

from semantic_version import Version


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
            return self.run(['rev-parse', '--is-inside-work-tree'], cwd=path) == 'true'
        except GitCommandError:
            return False

    def prepare_branch(self, repo, path, branch=None, with_submodules=True, shallow=False):
        """
        Checkout required branch to desired path. Clones a repo, if necessary
        """

        # TODO: add support for shallow clones with shallow submodules
        # TODO: add support for changing branches in all cases
        # TODO: check for valid remote
        # Check if target dir is already a valid repo
        if self.is_git_dir(path):
            self.run(['fetch', 'origin'])
            # Checkout required branch
            self.run(['checkout', '--force', branch or 'origin/HEAD'])
            # And remove all untracked files
            self.run(['reset', '--hard'])

            if with_submodules:
                self.run(['submodule', 'update', '--init', '--recursive'])

        else:
            shallow_clone_params = [
                '--depth',
                '1',
                '--single-branch',
            ]

            # Remove non empty dir if any
            clone_params = ['clone', repo]

            if branch:
                clone_params += ['--branch', branch]

            if shallow:
                clone_params += shallow_clone_params

            if with_submodules:
                clone_params += ['--recurse-submodules']

            clone_params.append(path)
            self.run(clone_params)

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
            raise GitCommandError("'git %s' failed with exit code %d" % (' '.join(args), e.returncode))

    def check_version(
            self,
            min_supported='2.13',  # As for Aug 2019 2.13 is the oldest supported version of git
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
