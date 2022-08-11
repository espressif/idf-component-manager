# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
from pathlib import Path

import pytest

from idf_component_tools.file_tools import copy_filtered_directory, filtered_paths


@pytest.fixture
def assets_path(tmp_path, fixtures_path):
    templatepath = Path(fixtures_path) / 'hash_examples' / 'component_4'
    # Avoid `dirs_exist_ok=True` missing in python 2
    subdir = tmp_path / 'sub'
    shutil.copytree(templatepath.as_posix(), subdir.as_posix())
    return subdir.as_posix()


def test_filtered_path_default(assets_path):
    assert filtered_paths(assets_path) == set(
        [
            Path(assets_path, '1.txt'),
            Path(assets_path, 'ignore.dir'),
            Path(assets_path, 'ignore.dir', 'file.txt'),
            Path(assets_path, 'ignore.me'),
        ])


def test_filtered_path_exclude_file(assets_path):
    assert filtered_paths(
        assets_path, exclude=['**/file.txt']) == set(
            [
                Path(assets_path, '1.txt'),
                Path(assets_path, 'ignore.dir'),
                Path(assets_path, 'ignore.me'),
            ])


def test_filtered_path_keep_empty_dir(assets_path):
    assert filtered_paths(
        assets_path, exclude=[
            'ignore.dir/**/*',
        ]) == set([
            Path(assets_path, '1.txt'),
            Path(assets_path, 'ignore.me'),
            Path(assets_path, 'ignore.dir'),
        ])


def test_filtered_path_exclude_empty_dir(assets_path):
    assert filtered_paths(
        assets_path, exclude=[
            'ignore.dir',
            'ignore.dir/*',
        ]) == set([
            Path(assets_path, '1.txt'),
            Path(assets_path, 'ignore.me'),
        ])


def test_filtered_path_exclude_dir_with_file(assets_path):
    extra_path = Path(assets_path, 'ignore.dir', 'extra').as_posix()
    os.mkdir(extra_path)
    one_more = os.path.join(extra_path, 'one_more.txt')
    shutil.copy(os.path.join(assets_path, '1.txt'), one_more)

    assert os.path.exists(one_more)

    assert filtered_paths(
        assets_path, exclude=[
            'ignore.dir/*',
        ]) == set(
            [
                Path(assets_path, '1.txt'),
                Path(assets_path, 'ignore.dir'),
                Path(assets_path, 'ignore.dir', 'extra', 'one_more.txt'),
                Path(assets_path, 'ignore.me'),
            ])


def test_excluded_and_included_files(tmpdir_factory):
    folders_with_subdirectories = tmpdir_factory.mktemp('folders_with_subdirectories')
    temp_dir = tmpdir_factory.mktemp('temp_dir')

    folder1 = folders_with_subdirectories.mkdir('folder1')
    f = folder1.mkdir('folder1_1').mkdir('folder1_1_1').join('test_file')
    f.write(u'Test file')

    f = folder1.mkdir('folder1_2').join('test_file')
    f.write(u'Test file')

    f = folders_with_subdirectories.mkdir('folder2').join('test_file')
    f.write(u'Test file')

    copy_filtered_directory(
        folders_with_subdirectories.strpath,
        temp_dir.strpath,
        include=['folder1/folder1_1/**/*', 'folder1/folder1_2/**/*'],
        exclude=['**/*'])

    assert os.listdir(temp_dir.strpath) == ['folder1']
