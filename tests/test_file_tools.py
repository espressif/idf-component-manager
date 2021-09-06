import os
import shutil
from pathlib import Path

import pytest

from idf_component_tools.file_tools import filtered_paths


@pytest.fixture
def assets_path(tmp_path):
    templatepath = Path(os.path.dirname(os.path.realpath(__file__))) / 'fixtures' / 'hash_examples' / 'component_4'
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
