# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from io import open

import pytest

from idf_component_tools.errors import GitError
from idf_component_tools.git_client import GitClient, GitCommandError


@pytest.fixture(scope='session')
def git_repository_with_two_branches(tmpdir_factory):
    temp_dir = tmpdir_factory.mktemp('git_repo')
    subprocess.check_output(['git', 'init', temp_dir.strpath])

    subprocess.check_output(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir.strpath)
    subprocess.check_output(['git', 'config', 'user.name', 'Test Test'], cwd=temp_dir.strpath)

    subprocess.check_output(['git', 'checkout', '-b', 'default'], cwd=temp_dir.strpath)

    f = temp_dir.mkdir('component1').join('test_file')
    f.write(u'component1')

    subprocess.check_output(['git', 'add', '*'], cwd=temp_dir.strpath)
    subprocess.check_output(['git', 'commit', '-m', '"Init commit"'], cwd=temp_dir.strpath)

    main_commit_id = subprocess.check_output(['git', 'rev-parse', 'default'], cwd=temp_dir.strpath).strip()

    subprocess.check_output(['git', 'checkout', '-b', 'new_branch'], cwd=temp_dir.strpath)

    f = temp_dir.mkdir('component2').join('test_file')
    f.write(u'component2')

    subprocess.check_output(['git', 'add', '*'], cwd=temp_dir.strpath)
    subprocess.check_output(['git', 'commit', '-m', '"Add new branch"'], cwd=temp_dir.strpath)

    branch_commit_id = subprocess.check_output(['git', 'rev-parse', 'new_branch'], cwd=temp_dir.strpath).strip()
    subprocess.check_output(['git', 'checkout', 'default'], cwd=temp_dir.strpath)

    return {
        'path': temp_dir.strpath,
        'default_head': main_commit_id.decode('utf-8'),
        'new_branch_head': branch_commit_id.decode('utf-8')
    }


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
