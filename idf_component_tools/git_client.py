# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
import re
import subprocess  # noqa: S404
import time
import typing as t
from datetime import datetime
from functools import wraps

from .errors import GitError
from .messages import warn
from .semver import Version


class GitCommandError(Exception):
    """
    Exception class for git errors.

    Git error that is supposed to be handled in the code in the code of this class,
    not in the user code.
    """

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        self.exit_code = kwargs.get('exit_code')
        super().__init__(*args)


def clean_tag_version(tag: str) -> str:
    """Clean version from tag before processing it"""
    tag = tag.strip()

    # Remove leading 'v' from tag
    if tag.startswith('v'):
        tag = tag[1:]

    # Replace revision 1.2.3.4 with 1.2.3~4
    tag = re.sub(r'^(\d+\.\d+\.\d+)\.(\d+)', r'\1~\2', tag)

    return tag


class GitClient:
    """Set of tools for working with git repos"""

    def __init__(
        self, git_command: str = 'git', min_supported: t.Union[str, Version] = '2.0.0'
    ) -> None:
        self.git_command = git_command or 'git'
        self.git_min_supported = (
            min_supported if isinstance(min_supported, Version) else Version(min_supported)
        )

        self._git_checked = False
        self._repo_updated = False

    def _git_cmd(func: t.Union[GitClient, t.Callable[..., t.Any]]) -> t.Callable:
        @wraps(func)  # type: ignore
        def wrapper(self, *args, **kwargs):
            if not self._git_checked:
                self.check_version()
                self._git_checked = True

            try:
                return func(self, *args, **kwargs)
            except GitCommandError as e:
                raise GitError(e)

        return wrapper

    def _update_bare_repo(self, *args, **kwargs):
        repo = kwargs.get('repo') or args[0]
        bare_path = kwargs.get('bare_path') or args[1]
        if not os.path.exists(bare_path):
            os.makedirs(bare_path)

        if not os.listdir(bare_path):
            self.run(['init', '--bare'], cwd=bare_path)
            self.run(['remote', 'add', 'origin', '--tags', '--mirror=fetch', repo], cwd=bare_path)

        if self.run(['config', '--get', 'remote.origin.url'], cwd=bare_path) != repo:
            self.run(['remote', 'set-url', 'origin', repo], cwd=bare_path)

        fetch_file = os.path.join(bare_path, 'FETCH_HEAD')
        current_time = time.mktime(datetime.now().timetuple())

        # Don't fetch too often, at most once a minute
        if not os.path.isfile(fetch_file) or current_time - os.stat(fetch_file).st_mtime > 60:
            self.run(['fetch', 'origin'], cwd=bare_path)

    def _bare_repo(func: t.Union[GitClient, t.Callable[..., t.Any]]) -> t.Callable:
        @wraps(func)  # type: ignore
        def wrapper(self, *args, **kwargs):
            if not self._repo_updated:
                self._update_bare_repo(*args, **kwargs)
                self._repo_updated = True

            return func(self, *args, **kwargs)

        return wrapper

    @_git_cmd
    def commit_id(self, path: str) -> str:
        return self.run(['show', '--format="%H"', '--no-patch'], cwd=path)

    @_git_cmd
    def is_dirty(self, path: str) -> bool:
        try:
            self.run(['diff', '--quiet'], cwd=path)
            return False
        except GitCommandError:
            return True

    @_git_cmd
    def is_git_dir(self, path: str) -> bool:
        try:
            return self.run(['rev-parse', '--is-inside-work-tree'], cwd=path).strip() == 'true'
        except GitCommandError:
            return False

    @_git_cmd
    @_bare_repo
    def prepare_ref(
        self,
        repo: str,
        bare_path: str,
        checkout_path: str,
        ref: t.Optional[str] = None,
        with_submodules: bool = True,
        selected_paths: t.Optional[t.List[str]] = None,
    ) -> str:
        """
        Checkout required branch to desired path. Create a bare repo, if necessary

        Parameters
        ----------
        repo: str
            URL of the repository
        bare_path: str
            Path to the bare repository
        checkout_path: str
            Path to checkout working repository
        ref: str
            Branch name, commit id or '*'
        with_submodules: bool
             If True, submodules will be downloaded
        selected_paths: t.List[str]
            List of folders and files that need to download
        Returns
        -------
            Commit id of the current checkout
        """
        commit_id = self.get_commit_id_by_ref(repo, bare_path, ref)

        # Checkout required branch
        checkout_command = [
            '--work-tree',
            checkout_path,
            '--git-dir',
            bare_path,
            'checkout',
            '--force',
            commit_id,
        ]
        if selected_paths:
            if '.gitmodules' not in selected_paths and self.has_gitmodules_by_ref(
                repo, bare_path, commit_id
            ):
                # avoid submodule update failed
                selected_paths += ['.gitmodules']
            checkout_command += ['--'] + selected_paths
        self.run(checkout_command)

        # And remove all untracked files
        self.run(['--work-tree', checkout_path, '--git-dir', bare_path, 'clean', '--force'])
        # Submodules
        if with_submodules:
            self.run([
                '--work-tree=.',
                '-C',
                checkout_path,
                '--git-dir',
                bare_path,
                'submodule',
                'update',
                '--init',
                '--recursive',
            ])

        return commit_id

    @_git_cmd
    @_bare_repo
    def get_commit_id_by_ref(self, repo: str, bare_path: str, ref: str) -> str:
        if ref:
            # If branch is provided check that exists
            try:
                self.run(['branch', '--contains', ref], cwd=bare_path)
            except GitCommandError:
                raise GitError(f'Branch "{ref}" doesn\'t exist in repo "{repo}"')

        else:
            # Set to latest commit from remote's HEAD
            ref = self.run(['ls-remote', '--exit-code', 'origin', 'HEAD'], cwd=bare_path)[:40]

        return self.run(['rev-parse', '--verify', ref], cwd=bare_path).strip()

    @_git_cmd
    @_bare_repo
    def has_gitmodules_by_ref(self, repo: str, bare_path: str, ref: str) -> bool:
        return (
            '.gitmodules' in self.run(['ls-tree', '--name-only', ref], cwd=bare_path).splitlines()
        )

    def run(self, args, cwd=None, env=None):
        """
        Executes a Git command with the given arguments.

        Args:
            args (t.List[str]): The list of command-line arguments for the Git command.
            cwd (str | None):
                The current working directory for the Git command.
                If None, the current working directory is used.
            env (dict | None):
                The environment variables for the Git command.
                If None, the current environment variables are used.

        Returns:
            str: The output of the Git command as a string.

        Raises:
            GitCommandError: If the Git command fails with a non-zero exit code.
        """
        if cwd is None:
            cwd = os.getcwd()
        env_copy = dict(os.environ)
        if env:
            env_copy.update(env)

        p = subprocess.Popen(
            [self.git_command] + list(args),  # noqa: S603
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env_copy,
        )
        stdout, stderr = p.communicate()

        if p.returncode == 0:
            if stderr:
                warn(stderr.decode('utf-8'))
        else:
            raise GitCommandError(
                "'git {}' failed with exit code {} \n{}\n{}".format(
                    ' '.join(args), p.returncode, stderr.decode('utf-8'), stdout.decode('utf-8')
                ),
                exit_code=p.returncode,
            )

        return stdout.decode('utf-8')

    def check_version(self) -> None:
        version = self.version()

        if version < self.git_min_supported:
            raise GitError(
                'Your git version %s is older than minimally required %s.'
                % (
                    version,
                    self.git_min_supported,
                )
            )

    def version(self) -> Version:
        try:
            git_version_str = subprocess.check_output(
                [self.git_command, '--version'],  # noqa: S603
                stderr=subprocess.STDOUT,
            ).decode('utf-8')
        except OSError:
            raise GitError('"git" command was not found')

        ver_match = re.match(r'^git version (\d+\.\d+\.\d+)', git_version_str)

        try:
            if ver_match:
                return Version(ver_match.group(1))
            else:
                raise GitCommandError()
        except (IndexError, ValueError, GitCommandError):
            raise GitError('Cannot recognize git version')

    @_git_cmd
    def get_tag_version(self, cwd: t.Optional[str] = None) -> Version:
        """
        Return a valid component version of the current commit if it is tagged,
        otherwise a `GitError` is raised.
        """

        try:
            tag_str = self.run(['describe', '--tags', '--exact-match'], cwd=cwd)
        except GitCommandError as e:
            if e.exit_code == 128:
                raise GitError('Not a tagged commit, cannot get version')
            else:
                raise GitError(f'Cannot get tag version due to git error\n{e}')

        try:
            semantic_version = Version(clean_tag_version(tag_str))
            return semantic_version
        except ValueError:
            raise GitError(f'Git tag does not contain a valid component version: {tag_str}')
