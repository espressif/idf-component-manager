# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import filecmp
import logging
import os
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from idf_component_manager.core import get_validated_manifest
from idf_component_tools import LOGGING_NAMESPACE
from idf_component_tools.errors import ManifestError, RunningEnvironmentError
from idf_component_tools.manager import ManifestManager, UploadMode


def test_check_filename(tmp_path):
    parser = ManifestManager(tmp_path, name='test')

    assert parser.path == tmp_path / 'idf_component.yml'


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
        YAML().dump(valid_manifest, fw)

    test_dump_path = tmp_path / 'test'
    test_dump_path.mkdir()

    manager = ManifestManager(manifest_path, name='test')
    manager.dump(str(test_dump_path))

    assert filecmp.cmp(manifest_path, test_dump_path / 'idf_component.yml')


def test_validate_env_not_expanded(valid_manifest, tmp_path):
    valid_manifest['targets'] = ['$SUPPORT_TARGET']
    valid_manifest['dependencies']['test']['rules'] = [{'if': 'target == $CURRENT_TARGET'}]
    valid_manifest['dependencies']['test']['matches'] = [{'if': 'idf_version == $CURRENT_IDF'}]

    manifest_path = tmp_path / 'idf_component.yml'
    with open(manifest_path, 'w') as fw:
        YAML().dump(valid_manifest, fw)

    manager = ManifestManager(manifest_path, name='test')

    # Check that it doesn't raise an error
    manager.load()

    test_dump_path = tmp_path / 'test'
    test_dump_path.mkdir()

    manager.dump(str(test_dump_path))

    assert filecmp.cmp(manifest_path, test_dump_path / 'idf_component.yml')


def test_dump_does_not_add_fields(tmp_path):
    manifest_path = tmp_path / 'idf_component.yml'
    manifest_content = 'version: 1.0.0\n'
    manifest_path.write_text(manifest_content)
    manager = ManifestManager(manifest_path, name='tst')

    test_dump_path = tmp_path / 'test'
    test_dump_path.mkdir()
    manager.dump(test_dump_path)

    dumped_manifest_content = (test_dump_path / 'idf_component.yml').read_text()
    assert manifest_content == dumped_manifest_content


def test_get_validated_manifest(valid_manifest, tmp_path):
    manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
    with open(manifest_path, 'w') as fw:
        YAML().dump(valid_manifest, fw)

    manager = ManifestManager(manifest_path, name='test', upload_mode=True)
    manifest = get_validated_manifest(manager, tmp_path)

    assert manifest.name == 'test'
    assert manifest.version == '2.3.1~2'


def test_get_validated_manifest_unexpected_file(valid_manifest, tmp_path, caplog):
    manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
    with open(manifest_path, 'w') as fw:
        YAML().dump(valid_manifest, fw)

    # Create CMakeCache.txt file in tmp_path
    Path(tmp_path / 'CMakeCache.txt').touch()

    manager = ManifestManager(manifest_path, name='test', upload_mode=True)
    with caplog.at_level(logging.WARNING, logger=LOGGING_NAMESPACE):
        get_validated_manifest(manager, tmp_path)
        assert len(caplog.records) == 1
        assert (
            'Unexpected files "CMakeCache.txt" found in the component directory "."'
            in caplog.records[0].message
        )

    Path(tmp_path / 'CMakeCache.txt').unlink()


def test_get_validated_manifest_invalid_component_manifest(valid_manifest, tmp_path):
    manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')

    with open(manifest_path, 'w') as fw:
        valid_manifest['version'] = 'invalid'
        YAML().dump(valid_manifest, fw)

    manager = ManifestManager(manifest_path, name='test', upload_mode=True)

    with pytest.raises(ManifestError, match='Manifest is not valid'):
        get_validated_manifest(manager, tmp_path)


def test_env_not_expanded_with_example_manifest(valid_manifest, tmp_path):
    valid_manifest['dependencies']['test']['rules'] = [{'if': '$MY_IDF_VAR == 1'}]
    manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
    with open(manifest_path, 'w') as fw:
        YAML().dump(valid_manifest, fw)

    with pytest.raises(RunningEnvironmentError):
        ManifestManager(manifest_path, name='test', upload_mode=UploadMode.component).load()

    ManifestManager(manifest_path, name='test', upload_mode=UploadMode.example).load()
