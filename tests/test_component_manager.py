# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
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
import yaml
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


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_init_project.yaml')
def test_init_project(mock_registry, tmp_path):
    tempdir = str(tmp_path)
    try:
        os.makedirs(os.path.join(tempdir, 'main'))
        os.makedirs(os.path.join(tempdir, 'components', 'foo'))
        main_manifest_path = os.path.join(tempdir, 'main', MANIFEST_FILENAME)
        foo_manifest_path = os.path.join(tempdir, 'components', 'foo', MANIFEST_FILENAME)

        manager = ComponentManager(path=tempdir)
        manager.create_manifest()
        manager.create_manifest(component='foo')

        for filepath in [main_manifest_path, foo_manifest_path]:
            with open(filepath, mode='r') as file:
                assert file.readline().startswith('## IDF Component Manager')

        manager.add_dependency('cmp==4.0.3')
        manifest_manager = ManifestManager(main_manifest_path, 'main')
        assert manifest_manager.manifest_tree['dependencies']['espressif/cmp'] == '==4.0.3'

        manager.add_dependency('espressif/cmp==4.0.3', component='foo')
        manifest_manager = ManifestManager(foo_manifest_path, 'foo')
        assert manifest_manager.manifest_tree['dependencies']['espressif/cmp'] == '==4.0.3'

    finally:
        shutil.rmtree(tempdir)


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_init_project_with_path.yaml')
def test_init_project_with_path(mock_registry, tmp_path):
    tempdir = str(tmp_path)
    try:
        os.makedirs(os.path.join(tempdir, 'src'))
        src_path = os.path.join(tempdir, 'src')
        src_manifest_path = os.path.join(src_path, MANIFEST_FILENAME)

        outside_project_path = str(Path(tempdir).parent)
        outside_project_path_error_match = 'Directory ".*" is not under project directory!'
        component_and_path_error_match = 'Cannot determine manifest directory.'

        manager = ComponentManager(path=tempdir)
        manager.create_manifest(path=src_path)

        with pytest.raises(FatalError, match=outside_project_path_error_match):
            manager.create_manifest(path=outside_project_path)

        with pytest.raises(FatalError, match=component_and_path_error_match):
            manager.create_manifest(component='src', path=src_path)

        manager.add_dependency('espressif/cmp==4.0.3', path=src_path)
        manifest_manager = ManifestManager(src_manifest_path, 'src')

        assert manifest_manager.manifest_tree['dependencies']['espressif/cmp'] == '==4.0.3'

        with pytest.raises(FatalError, match=outside_project_path_error_match):
            manager.create_manifest(path=outside_project_path)

        with pytest.raises(FatalError, match=component_and_path_error_match):
            manager.add_dependency('espressif/cmp==4.0.3', component='src', path=src_path)

    finally:
        shutil.rmtree(tempdir)


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_upload_component.yaml')
def test_upload_component(mock_registry, pre_release_component_path, capsys):
    manager = ComponentManager(path=pre_release_component_path)

    manager.upload_component('cmp')
    captured = capsys.readouterr()

    assert 'WARNING: URL field is missing in the manifest file' in captured.err


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_check_only_component.yaml')
def test_check_only_upload_component(mock_registry, pre_release_component_path):
    manager = ComponentManager(path=pre_release_component_path)

    manager.upload_component(
        'cmp',
        check_only=True,
    )


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_allow_existing_component.yaml')
def test_allow_existing_component(mock_registry, release_component_path, tmp_path):
    shutil.copytree(release_component_path, str(tmp_path / 'cmp'))
    manager = ComponentManager(path=str(tmp_path / 'cmp'))

    manager.upload_component(
        'cmp',
        allow_existing=True,
    )


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_validate_component.yaml')
def test_validate_component(mock_registry, pre_release_component_path):
    manager = ComponentManager(path=pre_release_component_path)

    manager.upload_component(
        'cmp',
        dry_run=True,
    )


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_upload_component_skip_pre.yaml')
def test_upload_component_skip_pre(mock_registry, pre_release_component_path):
    manager = ComponentManager(path=pre_release_component_path)

    with pytest.raises(NothingToDoError) as e:
        manager.upload_component(
            'cmp',
            skip_pre_release=True,
        )

        assert str(e.value).startswith('Skipping pre-release')


def remove_version_line(path):
    with open(os.path.join(str(path), MANIFEST_FILENAME), 'r+') as f:
        lines = f.readlines()
        f.seek(0)
        f.writelines(lines[1:])
        f.truncate()


def test_pack_component_version_from_git(monkeypatch, tmp_path, pre_release_component_path):
    copy_tree(pre_release_component_path, str(tmp_path))
    component_manager = ComponentManager(path=str(tmp_path))

    # remove the first version line
    remove_version_line(tmp_path)

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
    remove_version_line(tmp_path)

    component_manager.pack_component('cmp', '2.3.4')

    tempdir = os.path.join(tempfile.tempdir, 'cmp')
    unpack_archive(os.path.join(component_manager.dist_path, 'cmp_2.3.4.tgz'), tempdir)
    manifest = ManifestManager(tempdir, 'cmp', check_required_fields=True).load()
    assert manifest.version == '2.3.4'


def test_pack_component_with_examples(tmp_path, example_component_path):
    project_path = tmp_path / 'cmp'
    copy_tree(example_component_path, str(project_path))
    component_manager = ComponentManager(path=str(project_path))

    component_manager.pack_component('cmp', '2.3.4')

    unpack_archive(str(Path(component_manager.dist_path, 'cmp_2.3.4.tgz')), str(tmp_path / 'unpack'))

    assert (tmp_path / 'unpack' / 'examples' / 'cmp_ex').is_dir()
    assert 'cmake_minimum_required(VERSION 3.16)' in (tmp_path / 'unpack' / 'examples' / 'cmp_ex' /
                                                      'CMakeLists.txt').read_text()


def test_pack_component_with_rules_if(tmp_path, release_component_path, valid_optional_dependency_manifest_with_idf):
    project_path = tmp_path / 'cmp'
    copy_tree(release_component_path, str(project_path))
    with open(str(project_path / MANIFEST_FILENAME), 'w') as fw:
        yaml.dump(valid_optional_dependency_manifest_with_idf, fw)

    component_manager = ComponentManager(path=str(project_path))
    component_manager.pack_component('cmp', '2.3.4')


@pytest.mark.parametrize(
    'examples, message', [
        (
            [{
                'path': './custom_example_path/cmp_ex'
            }, {
                'path': './custom_example_path_2/cmp_ex'
            }], 'Examples from "./custom_example_path/cmp_ex" and "./custom_example_path_2/cmp_ex" '
            'have the same name: cmp_ex.'),
        (
            [{
                'path': './custom_example_path'
            }, {
                'path': './custom_example_path'
            }], 'Some paths in the `examples` block in the manifest are listed multiple times: ./custom_example_path'),
        ([{
            'path': './unknown_path'
        }], 'Example directory doesn\'t exist:*'),
    ])
def test_pack_component_with_examples_errors(tmp_path, example_component_path, examples, message):
    project_path = tmp_path / 'cmp'
    copy_tree(example_component_path, str(project_path))
    if len(examples) == 2 and examples[0] != examples[1]:  # Add second example
        copy_tree(str(Path(example_component_path, 'custom_example_path')), str(project_path / 'custom_example_path_2'))

    component_manager = ComponentManager(path=str(project_path))

    # Add folder with the same name of the example
    manifest_manager = ManifestManager(str(project_path), 'cmp', check_required_fields=True, version='2.3.4')
    manifest_manager.manifest_tree['examples'] = examples
    manifest_manager.dump(str(project_path))

    with pytest.raises(FatalError, match=message):
        component_manager.pack_component('cmp', '2.3.4')


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


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_component_not_exist.yaml')
def test_create_example_component_not_exist(tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    with raises(FatalError, match='Component "espressif/test" not found'):
        manager.create_project_from_example('test:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_not_exist.yaml')
def test_create_example_version_not_exist(mock_registry, tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    with raises(FatalError, match='Version of the component "test/cmp" satisfying the spec "=2.0.0" was not found.'):
        manager.create_project_from_example('test/cmp=2.0.0:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_not_exist.yaml')
def test_create_example_not_exist(mock_registry, tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    with raises(FatalError, match='Cannot find example "example" for "test/cmp" version "=1.0.1"'):
        manager.create_project_from_example('test/cmp=1.0.1:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_success.yaml')
def test_create_example_success(mock_registry, tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    manager.create_project_from_example('test/cmp>=1.0.0:sample_project')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_yank_version_success.yaml')
def test_yank_component_version(mock_registry, tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    manager.yank_version('cmp', '1.1.0', 'critical test', namespace='test')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_yank_version_success.yaml')
def test_yank_component_version_not_exists(mock_registry, tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    with raises(FatalError, match='Version 1.2.0 of the component \"test/cmp\" is not on the registry'):
        manager.yank_version('cmp', '1.2.0', 'critical test', namespace='test')
