# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import filecmp
import os

import pytest
import yaml

from idf_component_tools.errors import ManifestError
from idf_component_tools.manager import ManifestManager


def test_check_filename(tmp_path):
    path = tmp_path.as_posix()
    parser = ManifestManager(path, name='test')

    assert parser.path == os.path.join(path, 'idf_component.yml')


def test_parse_invalid_yaml(fixtures_path):
    manifest_path = os.path.join(fixtures_path, 'invalid_yaml.yml')
    parser = ManifestManager(manifest_path, name='fixtures')

    with pytest.raises(ManifestError) as e:
        parser.load()

    assert e.type == ManifestError
    assert str(e.value) == 'Manifest is not valid'


def test_parse_valid_yaml(fixtures_path):
    manifest_path = os.path.join(fixtures_path, 'idf_component.yml')
    parser = ManifestManager(manifest_path, name='fixtures')

    assert len(parser.manifest_tree.keys()) == 7


def test_prepare(fixtures_path):
    manifest_path = os.path.join(fixtures_path, 'idf_component.yml')
    parser = ManifestManager(manifest_path, name='fixtures')

    parser.load()

    assert parser.is_valid


def test_env_var_with_escaped_dollar_sign(valid_manifest, tmp_path):
    valid_manifest['description'] = '$$foo$$$$$$bar'
    manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
    with open(manifest_path, 'w') as fw:
        yaml.dump(valid_manifest, fw)

    test_dump_path = tmp_path / 'test'
    test_dump_path.mkdir()

    manager = ManifestManager(manifest_path, name='test')
    manager.dump(str(test_dump_path))

    assert filecmp.cmp(manifest_path, test_dump_path / 'idf_component.yml')


def test_validate_env_not_expanded(valid_manifest, tmp_path):
    valid_manifest['targets'] = ['$SUPPORT_TARGET']
    valid_manifest['dependencies']['test']['rules'] = [{'if': 'target == $CURRENT_TARGET'}]
    valid_manifest['dependencies']['test']['matches'] = [{'if': 'idf_version == $CURRENT_IDF'}]

    manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
    with open(manifest_path, 'w') as fw:
        yaml.dump(valid_manifest, fw)

    manager = ManifestManager(manifest_path, name='test')

    # Check that it doesn't raise an error
    manager.load()

    test_dump_path = tmp_path / 'test'
    test_dump_path.mkdir()

    manager.dump(str(test_dump_path))

    # Check that file is not modified
    assert filecmp.cmp(manifest_path, test_dump_path / 'idf_component.yml')
