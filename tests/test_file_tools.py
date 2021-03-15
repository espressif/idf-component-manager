import os
from pathlib import Path

from idf_component_tools.file_tools import filtered_paths

assets_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    'hash_examples',
    'component_4',
)


def test_filtered_path_default():
    assert filtered_paths(assets_path) == set(
        [
            Path(assets_path, '1.txt'),
            Path(assets_path, 'ignore.dir'),
            Path(assets_path, 'ignore.dir', 'file.txt'),
            Path(assets_path, 'ignore.me'),
        ])


def test_filtered_path_exclude_file():
    assert filtered_paths(
        assets_path, exclude=['**/file.txt']) == set(
            [
                Path(assets_path, '1.txt'),
                Path(assets_path, 'ignore.dir'),
                Path(assets_path, 'ignore.me'),
            ])


def test_filtered_path_exclude_dir():
    assert filtered_paths(
        assets_path, exclude=[
            'ignore.dir/*',
            'ignore.dir',
        ]) == set([
            Path(assets_path, '1.txt'),
            Path(assets_path, 'ignore.me'),
        ])
