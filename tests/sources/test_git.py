# SPDX-FileCopyrightText: 2022-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
import subprocess
import tempfile
import textwrap

import pytest

from idf_component_tools.git_client import GitClient
from idf_component_tools.hash_tools.calculate import hash_dir
from idf_component_tools.manager import ManifestManager
from idf_component_tools.manifest.models import ComponentRequirement
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


@pytest.fixture()
def git_repository_with_override_path(tmp_path):
    """Create a git repo with two components where one has an override_path dependency on the other."""
    repo_dir = tmp_path / 'override_repo'
    repo_dir.mkdir()

    # Create component_a at components/cmp_a with override_path dep on cmp_b
    cmp_a_dir = repo_dir / 'components' / 'cmp_a'
    cmp_a_dir.mkdir(parents=True)
    (cmp_a_dir / 'CMakeLists.txt').write_text('idf_component_register()')
    (cmp_a_dir / 'idf_component.yml').write_text(
        textwrap.dedent("""\
            version: 1.0.0
            dependencies:
              cmp_b:
                version: "*"
                override_path: "../cmp_b"
        """)
    )

    # Create component_b at components/cmp_b
    cmp_b_dir = repo_dir / 'components' / 'cmp_b'
    cmp_b_dir.mkdir(parents=True)
    (cmp_b_dir / 'CMakeLists.txt').write_text('idf_component_register()')
    (cmp_b_dir / 'idf_component.yml').write_text(
        textwrap.dedent("""\
            version: 2.0.0
        """)
    )

    subprocess.check_output(['git', 'init', repo_dir.as_posix()])
    subprocess.check_output(
        ['git', 'config', 'user.email', 'test@test.com'], cwd=repo_dir.as_posix()
    )
    subprocess.check_output(['git', 'config', 'user.name', 'Test Test'], cwd=repo_dir.as_posix())
    subprocess.check_output(['git', 'checkout', '-b', 'default'], cwd=repo_dir.as_posix())
    subprocess.check_output(['git', 'add', '.'], cwd=repo_dir.as_posix())
    subprocess.check_output(['git', 'commit', '-m', 'Init commit'], cwd=repo_dir.as_posix())

    return repo_dir


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


def test_resolve_override_path_to_git_dependency(git_repository_with_override_path):
    """Test that override_path in a git component's manifest is resolved to a git
    dependency pointing to the same repo and commit."""
    repo_path = git_repository_with_override_path.as_posix()

    source = GitSource(git=repo_path, path='components/cmp_a')
    component = source.versions('cmp_a')

    assert len(component.versions) == 1
    version = component.versions[0]

    # Should have one dependency (cmp_b), transformed to a git source
    assert len(version.dependencies) == 1
    dep = version.dependencies[0]
    assert dep.name == 'cmp_b'

    # The dependency should be a GitSource pointing to the same repo
    assert dep.source.type == 'git'
    assert dep.source.git == repo_path
    assert dep.source.path == os.path.join('components', 'cmp_b')

    # The version should be pinned to the same commit
    assert dep.version == str(version.version)


@pytest.mark.parametrize(
    'override_path',
    [
        '../../../outside_repo',
        './../../../../../../etc',
        '/absolute/path',
        '../../../../',
    ],
)
def test_resolve_override_path_outside_repo_falls_back_to_registry(override_path):
    """Test that override_path pointing outside the repo root falls back to registry with a warning."""
    source = GitSource(git='https://example.com/repo.git', path='components/cmp_a')

    dep = ComponentRequirement(
        name='external_cmp',
        version='>=1.0.0',
        override_path=override_path,
    )
    commit_id = 'abc123def456'

    result = source._resolve_override_paths([dep], commit_id)

    # Should fall back to registry — override_path dropped
    assert len(result) == 1
    assert result[0].source.type == 'service'
    assert result[0].override_path is None
    assert result[0].version == '>=1.0.0'


def test_resolve_override_path_preserves_non_override_deps():
    """Test that dependencies without override_path are passed through unchanged."""
    source = GitSource(git='https://example.com/repo.git', path='components/cmp_a')

    # A regular registry dependency (no override_path)
    dep_registry = ComponentRequirement(
        name='example/some_dep',
        version='>=1.0.0',
    )
    # A git dependency (already has git, should not be transformed)
    dep_git = ComponentRequirement(
        name='other_cmp',
        version='main',
        git='https://example.com/other.git',
        path='lib',
    )

    commit_id = 'abc123def456'
    result = source._resolve_override_paths([dep_registry, dep_git], commit_id)

    assert len(result) == 2
    assert result[0].source.type == 'service'
    assert result[1].source.type == 'git'
    assert result[1].source.git == 'https://example.com/other.git'
