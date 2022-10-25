# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
'''Test Core commands'''
import os
import shutil
import tempfile
from distutils.dir_util import copy_tree
from io import open
from pathlib import Path

import pytest
import vcr
from pytest import raises

from idf_component_manager.core import ComponentManager
from idf_component_tools.archive_tools import unpack_archive
from idf_component_tools.errors import FatalError, NothingToDoError
from idf_component_tools.git_client import GitClient
from idf_component_tools.manifest import MANIFEST_FILENAME, ManifestManager
from idf_component_tools.semver import Version


def list_dir(folder):
    res = []
    for root, _, files in os.walk(folder):
        for file in files:
            res.append(os.path.join(root, file))
    return res


def test_init_project():
    tempdir = tempfile.mkdtemp()

    try:
        os.makedirs(os.path.join(tempdir, 'main'))
        os.makedirs(os.path.join(tempdir, 'components', 'foo'))
        os.makedirs(os.path.join(tempdir, 'src'))
        main_manifest_path = os.path.join(tempdir, 'main', MANIFEST_FILENAME)
        foo_manifest_path = os.path.join(tempdir, 'components', 'foo', MANIFEST_FILENAME)
        src_path = os.path.join(tempdir, 'src')
        src_manifest_path = os.path.join(src_path, MANIFEST_FILENAME)

        outside_project_path = str(Path(tempdir).parent)
        outside_project_path_error_match = 'Directory ".*" is not under project directory!'
        component_and_path_error_match = 'Cannot determine manifest directory.'

        manager = ComponentManager(path=tempdir)
        manager.create_manifest()
        manager.create_manifest(component='foo')
        manager.create_manifest(path=src_path)

        with pytest.raises(FatalError, match=outside_project_path_error_match):
            manager.create_manifest(path=outside_project_path)

        with pytest.raises(FatalError, match=component_and_path_error_match):
            manager.create_manifest(component='src', path=src_path)

        for filepath in [main_manifest_path, foo_manifest_path]:
            with open(filepath, mode='r') as file:
                assert file.readline().startswith('## IDF Component Manager')

        manager.add_dependency('comp<=1.0.0')
        manifest_manager = ManifestManager(main_manifest_path, 'main')
        assert manifest_manager.manifest_tree['dependencies']['espressif/comp'] == '<=1.0.0'

        manager.add_dependency('idf/comp<=1.0.0', component='foo')
        manifest_manager = ManifestManager(foo_manifest_path, 'foo')
        assert manifest_manager.manifest_tree['dependencies']['idf/comp'] == '<=1.0.0'

        manager.add_dependency('idf/comp<=1.0.0', path=src_path)
        manifest_manager = ManifestManager(src_manifest_path, 'src')
        assert manifest_manager.manifest_tree['dependencies']['idf/comp'] == '<=1.0.0'

        with pytest.raises(FatalError, match=outside_project_path_error_match):
            manager.create_manifest(path=outside_project_path)

        with pytest.raises(FatalError, match=component_and_path_error_match):
            manager.add_dependency('idf/comp<=1.0.0', component='src', path=src_path)
    finally:
        shutil.rmtree(tempdir)


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_upload_component.yaml')
def test_upload_component(monkeypatch, pre_release_component_path):
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'http://localhost:5000')
    monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'test')
    manager = ComponentManager(path=pre_release_component_path)

    manager.upload_component('cmp')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_check_only_component.yaml')
def test_check_only_upload_component(monkeypatch, pre_release_component_path):
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'http://localhost:5000')
    monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'test')
    manager = ComponentManager(path=pre_release_component_path)

    manager.upload_component(
        'cmp',
        check_only=True,
    )


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_allow_existing_component.yaml')
def test_allow_existing_component(monkeypatch, release_component_path):
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'http://localhost:5000')
    monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'test')
    manager = ComponentManager(path=release_component_path)

    manager.upload_component(
        'cmp',
        allow_existing=True,
    )


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_upload_component_skip_pre.yaml')
def test_upload_component_skip_pre(monkeypatch, pre_release_component_path):
    manager = ComponentManager(path=pre_release_component_path)
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'http://localhost:5000')
    monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'test')

    with pytest.raises(NothingToDoError) as e:
        manager.upload_component(
            'cmp',
            skip_pre_release=True,
        )

        assert str(e.value).startswith('Skipping pre-release')


def test_pack_component_version_from_git(monkeypatch, tmp_path, pre_release_component_path):
    copy_tree(pre_release_component_path, str(tmp_path))
    component_manager = ComponentManager(path=str(tmp_path))

    # remove the first version line
    with open(os.path.join(str(tmp_path), MANIFEST_FILENAME), 'r+') as f:
        lines = f.readlines()
        f.seek(0)
        f.writelines(lines[1:])
        f.truncate()

    def mock_git_tag(self):
        return Version('3.0.0')

    monkeypatch.setattr(GitClient, 'get_tag_version', mock_git_tag)

    component_manager.pack_component('pre', 'git')

    tempdir = os.path.join(tempfile.tempdir, 'cmp_pre')
    unpack_archive(os.path.join(component_manager.dist_path, 'pre_3.0.0.tgz'), tempdir)
    manifest = ManifestManager(tempdir, 'pre', check_required_fields=True).load()
    assert manifest.version == '3.0.0'
    assert set(list_dir(tempdir)) == set(
        os.path.join(tempdir, file) for file in [
            'idf_component.yml',
            'cmp.c',
            'CMakeLists.txt',
            os.path.join('include', 'cmp.h'),
        ])


def test_pack_component_with_version(tmp_path, release_component_path):
    copy_tree(release_component_path, str(tmp_path))
    component_manager = ComponentManager(path=str(tmp_path))

    # remove the first version line
    with open(os.path.join(str(tmp_path), MANIFEST_FILENAME), 'r+') as f:
        lines = f.readlines()
        f.seek(0)
        f.writelines(lines[1:])
        f.truncate()

    component_manager.pack_component('cmp', '2.3.4')

    tempdir = os.path.join(tempfile.tempdir, 'cmp')
    unpack_archive(os.path.join(component_manager.dist_path, 'cmp_2.3.4.tgz'), tempdir)
    manifest = ManifestManager(tempdir, 'cmp', check_required_fields=True).load()
    assert manifest.version == '2.3.4'


def test_create_example_project_path_not_a_directory(tmp_path):
    existing_file = tmp_path / 'example'
    existing_file.write_text(u'test')

    manager = ComponentManager(path=str(tmp_path))

    with raises(FatalError, match='Your target path is not a directory*'):
        manager.create_project_from_example('test:example')


def test_create_example_project_path_not_empty(tmp_path):
    example_dir = tmp_path / 'example'
    example_dir.mkdir()
    existing_file = example_dir / 'test'
    existing_file.write_text(u'test')

    manager = ComponentManager(path=str(tmp_path))

    with raises(FatalError, match='To create an example you must*'):
        manager.create_project_from_example('test:example')


def test_create_example_component_not_exist(tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    with raises(FatalError, match='Selected component*'):
        manager.create_project_from_example('test:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_not_exist.yaml')
def test_create_example_version_not_exist(monkeypatch, tmp_path):
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'http://localhost:5000')
    manager = ComponentManager(path=str(tmp_path))
    with raises(FatalError, match='Version of the component "test/cmp" satisfying the spec "=2.0.0" was not found.'):
        manager.create_project_from_example('test/cmp=2.0.0:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_not_exist.yaml')
def test_create_example_not_exist(monkeypatch, tmp_path):
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'http://localhost:5000')
    manager = ComponentManager(path=str(tmp_path))
    with raises(FatalError, match='Cannot find example "example" for "test/cmp" version "=1.0.1"'):
        manager.create_project_from_example('test/cmp=1.0.1:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_success.yaml')
def test_create_example_success(monkeypatch, tmp_path):
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'http://localhost:5000')
    manager = ComponentManager(path=str(tmp_path))
    manager.create_project_from_example('test/cmp>=1.0.0:sample_project')
