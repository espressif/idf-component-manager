# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import shutil
import typing as t
from pathlib import Path

import pytest

from idf_component_tools import LOGGING_NAMESPACE
from idf_component_tools.file_tools import (
    check_unexpected_component_files,
    copy_filtered_directory,
    directory_size,
    filtered_paths,
    human_readable_size,
)


def create_gitignore(path: t.Union[str, Path], patterns: t.List[str]):
    gitignore = Path(path) / '.gitignore'
    gitignore.write_text('\n'.join(patterns))


@pytest.fixture
def assets_path(tmp_path, fixtures_path):
    templatepath = Path(fixtures_path) / 'hash_examples' / 'component_4'
    # Avoid `dirs_exist_ok=True` missing in python 2
    subdir = tmp_path / 'sub'
    shutil.copytree(templatepath.as_posix(), subdir.as_posix())
    return subdir


def test_filtered_path_default(assets_path):
    assert filtered_paths(assets_path) == {
        assets_path / '1.txt',
        assets_path / 'ignore.dir' / 'file.txt',
        assets_path / 'ignore.me',
    }


def test_filtered_path_no_default(assets_path):
    assert filtered_paths(assets_path, exclude_default=False) == {
        assets_path / '1.txt',
        assets_path / 'ignore.dir' / 'file.txt',
        assets_path / 'ignore.me',
        assets_path / '.gitlab-ci.yml',
    }


def test_filtered_path_exclude_file_and_empty_dirs(assets_path):
    assert filtered_paths(assets_path, exclude=['**/file.txt']) == {
        assets_path / '1.txt',
        assets_path / 'ignore.me',
    }


def test_filtered_path_exclude_file_and_empty_dir_kept(assets_path):
    assert filtered_paths(assets_path, exclude=['**/file.txt'], include=['ignore.dir']) == {
        assets_path / '1.txt',
        assets_path / 'ignore.me',
        assets_path / 'ignore.dir',
    }


def test_filtered_path_removes_empty_dir(assets_path):
    assert filtered_paths(
        assets_path,
        exclude=[
            'ignore.dir/**/*',
        ],
    ) == {
        assets_path / '1.txt',
        assets_path / 'ignore.me',
    }


def test_filtered_path_exclude_empty_dir(assets_path):
    assert filtered_paths(
        assets_path,
        exclude=[
            'ignore.dir',
            'ignore.dir/*',
        ],
    ) == {
        assets_path / '1.txt',
        assets_path / 'ignore.me',
    }


def test_filtered_path_exclude_dir_with_file(assets_path):
    extra_path = assets_path / 'ignore.dir' / 'extra'
    extra_path.mkdir(exist_ok=True)
    one_more = extra_path / 'one_more.txt'
    shutil.copy(assets_path / '1.txt', one_more)

    assert one_more.exists()

    assert filtered_paths(
        assets_path,
        exclude=[
            'ignore.dir/*',
        ],
    ) == {
        assets_path / '1.txt',
        assets_path / 'ignore.dir' / 'extra' / 'one_more.txt',
        assets_path / 'ignore.me',
    }


def test_filtered_with_default_path(tmp_path):
    (tmp_path / 'build_all.sh').touch()
    (tmp_path / 'build_me').mkdir()
    (tmp_path / 'build_me' / 'file').touch()

    assert filtered_paths(tmp_path, exclude_default=True) == {
        tmp_path / 'build_all.sh',
    }


def test_excluded_and_included_files(tmpdir_factory):
    folders_with_subdirectories = tmpdir_factory.mktemp('folders_with_subdirectories')
    temp_dir = tmpdir_factory.mktemp('temp_dir')

    folder1 = folders_with_subdirectories.mkdir('folder1')
    f = folder1.mkdir('folder1_1').mkdir('folder1_1_1').join('test_file')
    f.write('Test file')

    f = folder1.mkdir('folder1_2').join('test_file')
    f.write('Test file')

    f = folders_with_subdirectories.mkdir('folder2').join('test_file')
    f.write('Test file')

    copy_filtered_directory(
        folders_with_subdirectories.strpath,
        temp_dir.strpath,
        include=['folder1/folder1_1/**/*', 'folder1/folder1_2/**/*'],
        exclude=['**/*'],
    )

    assert os.listdir(temp_dir.strpath) == ['folder1']


def test_exclude_files_with_gitignore(assets_path):
    create_gitignore(assets_path, ['ignore.me', '1.txt'])

    assert filtered_paths(
        assets_path,
        use_gitignore=True,
    ) == {
        assets_path / 'ignore.dir' / 'file.txt',
        assets_path / '.gitignore',
        assets_path / '.gitlab-ci.yml',
    }


def test_exclude_directory_with_gitignore(assets_path):
    create_gitignore(assets_path, ['ignore.dir'])

    assert filtered_paths(
        assets_path,
        use_gitignore=True,
    ) == {
        assets_path / 'ignore.me',
        assets_path / '1.txt',
        assets_path / '.gitignore',
        assets_path / '.gitlab-ci.yml',
    }


def test_exclude_files_with_nested_gitignore(assets_path):
    create_gitignore(assets_path, ['ignore.me', '1.txt'])
    nested_dir = assets_path / 'nested.dir'
    nested_dir.mkdir()
    (nested_dir / 'file1.txt').write_text('1')
    (nested_dir / 'file2.txt').write_text('2')
    create_gitignore(nested_dir, ['file1.txt'])

    assert filtered_paths(
        assets_path,
        use_gitignore=True,
    ) == {
        assets_path / 'ignore.dir' / 'file.txt',
        assets_path / 'nested.dir' / 'file2.txt',
        assets_path / 'nested.dir' / '.gitignore',
        assets_path / '.gitignore',
        assets_path / '.gitlab-ci.yml',
    }


def test_include_empty_directory_with_keep_file(assets_path):
    create_gitignore(assets_path, ['ignore.dir/*', '!**/.keep'])
    ignore_dir = assets_path / 'ignore.dir'
    (ignore_dir / '.keep').write_text('1')

    assert filtered_paths(assets_path, use_gitignore=True) == {
        assets_path / 'ignore.dir' / '.keep',
        assets_path / '1.txt',
        assets_path / 'ignore.me',
        assets_path / '.gitignore',
        assets_path / '.gitlab-ci.yml',
    }


def test_exclude_files_with_gitignore_and_exclude(assets_path):
    create_gitignore(assets_path, ['ignore.me'])

    assert filtered_paths(assets_path, use_gitignore=True, exclude=['1.txt']) == {
        assets_path / 'ignore.dir' / 'file.txt',
        assets_path / '.gitignore',
        assets_path / '.gitlab-ci.yml',
    }


def test_no_default_exclude_with_gitignore(assets_path):
    create_gitignore(assets_path, ['ignore.me'])

    assert filtered_paths(assets_path, use_gitignore=True, exclude_default=True) == {
        assets_path / '1.txt',
        assets_path / 'ignore.dir' / 'file.txt',
        assets_path / '.gitignore',
        assets_path / '.gitlab-ci.yml',
    }


def test_include_files_excluded_by_gitignore(assets_path):
    create_gitignore(assets_path, ['examples', '1.txt'])
    examples_dir = assets_path / 'examples'
    examples_dir.mkdir()
    (examples_dir / 'test.txt').write_text('1')
    test_example = examples_dir / 'test_example'
    test_example.mkdir()
    (test_example / 'test.txt').write_text('1')

    assert filtered_paths(assets_path, use_gitignore=True, include=['examples/**/*', '1.txt']) == {
        assets_path / 'examples' / 'test_example' / 'test.txt',
        assets_path / 'examples' / 'test_example',
        assets_path / 'examples' / 'test.txt',
        assets_path / 'ignore.dir' / 'file.txt',
        assets_path / 'ignore.me',
        assets_path / '1.txt',
        assets_path / '.gitignore',
        assets_path / '.gitlab-ci.yml',
    }


def test_check_suspicious_component_files(release_component_path, tmp_path, caplog):
    sub = str(tmp_path / 'sub')
    shutil.copytree(release_component_path, sub)
    (Path(sub) / 'dev' / 'CMakeCache.txt').touch()

    with caplog.at_level(logging.WARNING, logger=LOGGING_NAMESPACE):
        check_unexpected_component_files(sub)
        assert len(caplog.records) == 1
        assert (
            'Unexpected files "CMakeCache.txt" found in the component directory "dev"'
            in caplog.records[0].message
        )


def test_directory_size(tmp_path, file_with_size):
    file1 = tmp_path / 'file1.txt'
    file2 = tmp_path / 'file2.txt'
    file_with_size(file1, 14)
    file_with_size(file2, 14)

    size = directory_size(str(tmp_path))

    assert size == 28


@pytest.mark.parametrize(
    ('size', 'expected'),
    [
        (123, '123 bytes'),
        (1523, '1.49 KB'),
        (1052523, '1.00 MB'),
        (1100523000, '1.02 GB'),
    ],
)
def test_human_readable_size(size, expected):
    assert human_readable_size(size) == expected


def test_human_readable_size_with_negative_size():
    with pytest.raises(ValueError):
        human_readable_size(-1)
