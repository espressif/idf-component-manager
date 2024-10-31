# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess

import pytest

from idf_component_tools.errors import GitError
from idf_component_tools.git_client import GitClient, clean_tag_version


@pytest.fixture()
def git_repository(tmpdir_factory):
    temp_dir = tmpdir_factory.mktemp('git_repo')
    subprocess.check_output(['git', 'init', temp_dir.strpath])

    subprocess.check_output(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir.strpath)
    subprocess.check_output(['git', 'config', 'user.name', 'Test Test'], cwd=temp_dir.strpath)

    subprocess.check_output(['git', 'checkout', '-b', 'default'], cwd=temp_dir.strpath)

    f = temp_dir.mkdir('component1').join('test_file')
    f.write('component1')

    subprocess.check_output(['git', 'add', '*'], cwd=temp_dir.strpath)
    subprocess.check_output(['git', 'commit', '-m', '"Init commit"'], cwd=temp_dir.strpath)

    return temp_dir


@pytest.fixture()
def git_repository_with_two_branches(git_repository):
    main_commit_id = subprocess.check_output(
        ['git', 'rev-parse', 'default'], cwd=git_repository.strpath
    ).strip()

    subprocess.check_output(['git', 'checkout', '-b', 'new_branch'], cwd=git_repository.strpath)

    f = git_repository.mkdir('component2').join('test_file')
    f.write('component2')

    subprocess.check_output(['git', 'add', '*'], cwd=git_repository.strpath)
    subprocess.check_output(['git', 'commit', '-m', '"Add new branch"'], cwd=git_repository.strpath)

    branch_commit_id = subprocess.check_output(
        ['git', 'rev-parse', 'new_branch'], cwd=git_repository.strpath
    ).strip()
    subprocess.check_output(['git', 'checkout', 'default'], cwd=git_repository.strpath)

    return {
        'path': git_repository.strpath,
        'default_head': main_commit_id.decode('utf-8'),
        'new_branch_head': branch_commit_id.decode('utf-8'),
    }


def test_bare_repository_in_cache(tmpdir_factory):
    client = GitClient()
    git_repo = 'test_repo'
    checkout_path = tmpdir_factory.mktemp('checkout_folder').strpath
    cache_path = tmpdir_factory.mktemp('cache_folder').strpath
    try:
        client.prepare_ref(
            repo=git_repo, bare_path=cache_path, checkout_path=checkout_path, with_submodules=True
        )
    except GitError:
        config_file = os.path.join(cache_path, 'config')

        with open(config_file, encoding='utf-8') as f:
            config = f.read()
            assert 'bare = true' in config


def test_working_with_git_without_branch(git_repository_with_two_branches, tmpdir_factory):
    client = GitClient()
    git_repo = git_repository_with_two_branches['path']
    checkout_path = tmpdir_factory.mktemp('checkout_folder').strpath
    cache_path = tmpdir_factory.mktemp('cache_folder').strpath
    commit_id = client.prepare_ref(
        repo=git_repo, bare_path=cache_path, checkout_path=checkout_path, with_submodules=True
    )
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
        selected_paths=['component2'],
    )
    assert commit_id == git_repository_with_two_branches['new_branch_head']


def test_git_branch_does_not_exist(git_repository_with_two_branches, tmpdir_factory):
    client = GitClient()
    git_repo = git_repository_with_two_branches['path']
    checkout_path = tmpdir_factory.mktemp('checkout_folder').strpath
    cache_path = tmpdir_factory.mktemp('cache_folder').strpath
    with pytest.raises(GitError, match='Git reference "branch_not_exists" doesn\'t exist *'):
        client.prepare_ref(
            repo=git_repo,
            bare_path=cache_path,
            checkout_path=checkout_path,
            ref='branch_not_exists',
            with_submodules=True,
            selected_paths=['component2'],
        )


def test_git_path_does_not_exist(git_repository_with_two_branches, tmpdir_factory):
    client = GitClient()
    git_repo = git_repository_with_two_branches['path']
    checkout_path = tmpdir_factory.mktemp('checkout_folder').strpath
    cache_path = tmpdir_factory.mktemp('cache_folder').strpath
    with pytest.raises(
        GitError, match=r"pathspec 'path_not_exists' did not match any file\(s\) known to git"
    ):
        client.prepare_ref(
            repo=git_repo,
            bare_path=cache_path,
            checkout_path=checkout_path,
            ref='new_branch',
            with_submodules=True,
            selected_paths=['path_not_exists'],
        )


@pytest.mark.parametrize(
    'input_str, expected_output',
    [
        ('v1.2.3', '1.2.3'),
        ('1.2.3.4', '1.2.3~4'),
        ('v1.2.3.4', '1.2.3~4'),
        ('v1.2.3.4-rc1', '1.2.3~4-rc1'),
        ('v1.2.3.4-rc1+123', '1.2.3~4-rc1+123'),
        ('abc', 'abc'),
    ],
)
def test_clean_tag_version(input_str, expected_output):
    assert clean_tag_version(input_str) == expected_output


def test_get_tag_version(git_repository):
    client = GitClient()
    git_repo = git_repository.strpath

    # Create a lightweight tag
    client.run(['tag', 'v1.2.3'], cwd=git_repo)
    assert str(client.get_tag_version(cwd=git_repo)) == '1.2.3'

    # Remove the tag
    client.run(['tag', '-d', 'v1.2.3'], cwd=git_repo)

    # Create an annotated tag
    client.run(['tag', '-a', 'v1.2.4', '-m', 'Test tag'], cwd=git_repo)
    assert str(client.get_tag_version(cwd=git_repo)) == '1.2.4'

    # Remove the tag
    client.run(['tag', '-d', 'v1.2.4'], cwd=git_repo)

    # Not a tag raises an error
    with pytest.raises(GitError, match='Not a tagged commit'):
        client.get_tag_version(cwd=git_repo)
