import os
from io import open

import pytest

from idf_component_tools.errors import GitError
from idf_component_tools.git_client import GitClient, GitCommandError


def test_bare_repository_in_cache(tmpdir_factory):
    client = GitClient()
    git_repo = 'test_repo'
    checkout_path = tmpdir_factory.mktemp('checkout_folder').strpath
    cache_path = tmpdir_factory.mktemp('cache_folder').strpath
    try:
        client.prepare_ref(repo=git_repo, bare_path=cache_path, checkout_path=checkout_path, with_submodules=True)
    except GitCommandError:
        config_file = os.path.join(cache_path, 'config')

        with open(config_file, 'r', encoding='utf-8') as f:
            config = f.read()
            assert 'bare = true' in config


def test_working_with_git_without_branch(git_repository_with_two_branches, tmpdir_factory):
    client = GitClient()
    git_repo = git_repository_with_two_branches['path']
    checkout_path = tmpdir_factory.mktemp('checkout_folder').strpath
    cache_path = tmpdir_factory.mktemp('cache_folder').strpath
    commit_id = client.prepare_ref(
        repo=git_repo, bare_path=cache_path, checkout_path=checkout_path, with_submodules=True)
    assert commit_id == git_repository_with_two_branches['default_head']


def test_working_with_git_with_branch(git_repository_with_two_branches, tmpdir_factory):
    client = GitClient()
    git_repo = git_repository_with_two_branches['path']
    checkout_path = tmpdir_factory.mktemp('checkout_folder').strpath
    cache_path = tmpdir_factory.mktemp('cache_folder').strpath
    commit_id = client.prepare_ref(
        repo=git_repo,
        bare_path=cache_path,
        checkout_path=checkout_path,
        ref='new_branch',
        with_submodules=True,
        selected_paths=['component2'])
    assert commit_id == git_repository_with_two_branches['new_branch_head']


def test_git_branch_does_not_exist(git_repository_with_two_branches, tmpdir_factory):
    client = GitClient()
    git_repo = git_repository_with_two_branches['path']
    checkout_path = tmpdir_factory.mktemp('checkout_folder').strpath
    cache_path = tmpdir_factory.mktemp('cache_folder').strpath
    with pytest.raises(GitError, match='Branch "branch_not_exists" doesn\'t exist *'):
        client.prepare_ref(
            repo=git_repo,
            bare_path=cache_path,
            checkout_path=checkout_path,
            ref='branch_not_exists',
            with_submodules=True,
            selected_paths=['component2'])
