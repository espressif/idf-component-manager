# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import shutil
import subprocess
import tempfile

import pytest

from idf_component_tools.git_client import GitClient
from idf_component_tools.hash_tools.calculate import hash_dir
from idf_component_tools.manager import ManifestManager
from idf_component_tools.sources import GitSource

COMMIT_ID = '38041fa9e7f8a79b8ff8cd247c73cf92b7e3c23a'


@pytest.fixture()
def git_repository_with_manifest(hash_component, tmp_path):
    temp_dir = tmp_path / 'git_repo'
    shutil.copytree(hash_component(5), temp_dir)

    subprocess.check_output(['git', 'init', temp_dir.as_posix()])

    subprocess.check_output(
        ['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir.as_posix()
    )
    subprocess.check_output(['git', 'config', 'user.name', 'Test Test'], cwd=temp_dir.as_posix())

    subprocess.check_output(['git', 'checkout', '-b', 'default'], cwd=temp_dir.as_posix())

    subprocess.check_output(['git', 'add', '*'], cwd=temp_dir.as_posix())
    subprocess.check_output(['git', 'commit', '-m', '"Init commit"'], cwd=temp_dir.as_posix())

    return temp_dir


def test_validate_version_spec_git():
    source = GitSource(git='foo')
    assert source.validate_version_spec(None)
    assert source.validate_version_spec('*')
    assert source.validate_version_spec('feature/new_test_branch')
    assert source.validate_version_spec('test_branch')
    assert source.validate_version_spec(COMMIT_ID)
    assert not source.validate_version_spec('..non_valid_branch')
    assert not source.validate_version_spec('@{non_valid_too')
    assert not source.validate_version_spec('wrong\\slash')


def test_normalize_spec(monkeypatch):
    source = GitSource(git='foo')
    monkeypatch.setattr(GitClient, 'get_commit_id_by_ref', lambda *_: COMMIT_ID)

    assert '*' == source.normalize_spec(None)
    assert COMMIT_ID == source.normalize_spec('*')


def test_checkout_git_source(monkeypatch):
    source = GitSource(git='foo')
    monkeypatch.setattr(GitClient, 'prepare_ref', lambda *args, **kwargs: COMMIT_ID)
    temp_path = tempfile.mkdtemp()

    assert COMMIT_ID == source._checkout_git_source('*', temp_path)


def test_versions_component_hash(git_repository_with_manifest):
    git_repo_path = git_repository_with_manifest.as_posix()

    # Calculate expected component hash
    manifest = ManifestManager(git_repo_path, '').load()
    expected_hash = hash_dir(
        git_repo_path, include=manifest.include_set, exclude=manifest.exclude_set
    )

    # Create source with defined git repository and call versions method
    source = GitSource(git=git_repo_path)
    component = source.versions('foo')

    # Check if component version hash is correct
    assert component.versions[0].component_hash == expected_hash
