# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import filecmp
import json
import os

import jsonschema
import pytest
import yaml

from idf_component_tools.errors import ManifestError
from idf_component_tools.manifest import JSON_SCHEMA, ComponentVersion, ManifestManager


class TestComponentVersion(object):
    def test_comparison(self):
        versions = [
            ComponentVersion('3.0.4'),
            ComponentVersion('3.0.6'),
            ComponentVersion('3.0.5'),
        ]

        assert versions[0] == ComponentVersion('3.0.4')
        assert versions[0] != ComponentVersion('*')
        assert versions[0] != ComponentVersion('699d3202533d13b55df3021d93352d8c242ee81e')
        assert str(max(versions)) == '3.0.6'

    def test_flags(self):
        semver = ComponentVersion('1.2.3')
        assert semver.is_semver
        assert not semver.is_commit_id
        assert not semver.is_any

        semver = ComponentVersion('*')
        assert not semver.is_semver
        assert not semver.is_commit_id
        assert semver.is_any

        semver = ComponentVersion('699d3202533d13b55df3021d93352d8c242ee81e')
        assert not semver.is_semver
        assert semver.is_commit_id
        assert not semver.is_any


class TestManifestPipeline(object):
    def test_check_filename(self, tmp_path):
        path = tmp_path.as_posix()
        parser = ManifestManager(path, name='test')

        assert parser.path == os.path.join(path, 'idf_component.yml')

    def test_parse_invalid_yaml(self, fixtures_path):
        manifest_path = os.path.join(fixtures_path, 'invalid_yaml.yml')
        parser = ManifestManager(manifest_path, name='fixtures')

        with pytest.raises(ManifestError) as e:
            parser.manifest_tree

        assert e.type == ManifestError
        assert str(e.value).startswith('Cannot parse')

    def test_parse_valid_yaml(self, capsys, fixtures_path):
        manifest_path = os.path.join(fixtures_path, 'idf_component.yml')
        parser = ManifestManager(manifest_path, name='fixtures')

        assert len(parser.manifest_tree.keys()) == 7

    def test_prepare(self, fixtures_path):
        manifest_path = os.path.join(fixtures_path, 'idf_component.yml')
        parser = ManifestManager(manifest_path, name='fixtures')

        parser.load()

        assert parser.is_valid

    def test_env_var(self, valid_manifest, monkeypatch, tmp_path):
        monkeypatch.setenv('SUPPORT_TARGET', 'esp32s2')
        valid_manifest['targets'] = ['$SUPPORT_TARGET']

        manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
        with open(manifest_path, 'w') as fw:
            yaml.dump(valid_manifest, fw)

        parser = ManifestManager(manifest_path, name='test', expand_environment=True)
        parser.load()

        assert parser.manifest_tree['targets'] == ['esp32s2']

    def test_env_var_with_escaped_dollar_sign(self, valid_manifest, tmp_path):
        valid_manifest['description'] = '$$foo$$$$$$bar'
        manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
        with open(manifest_path, 'w') as fw:
            yaml.dump(valid_manifest, fw)

        test_dump_path = os.path.join(str(tmp_path), 'test')
        os.mkdir(test_dump_path)

        parser = ManifestManager(manifest_path, name='test', expand_environment=True)
        parser.dump(str(test_dump_path))

        assert filecmp.cmp(
            manifest_path, os.path.join(test_dump_path, 'idf_component.yml'), shallow=False
        )

    def test_env_var_not_specified(self, valid_manifest, monkeypatch, tmp_path):
        valid_manifest['targets'] = ['$SUPPORT_TARGET']

        manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
        with open(manifest_path, 'w') as fw:
            yaml.dump(valid_manifest, fw)

        parser = ManifestManager(manifest_path, name='test', expand_environment=True)
        with pytest.raises(ManifestError, match='"SUPPORT_TARGET".*not set'):
            parser.load()

    def test_validate_env_not_expanded(self, valid_manifest, tmp_path):
        valid_manifest['targets'] = ['$SUPPORT_TARGET']
        valid_manifest['dependencies']['test']['rules'] = [{'if': 'target == $CURRENT_TARGET'}]

        manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
        with open(manifest_path, 'w') as fw:
            yaml.dump(valid_manifest, fw)

        parser = ManifestManager(manifest_path, name='test')
        parser.load()


def test_json_schema():
    schema_str = json.dumps(JSON_SCHEMA)

    try:
        validator = jsonschema.Draft7Validator
    except AttributeError:
        validator = jsonschema.Draft4Validator  # python 3.4

    validator.check_schema(json.loads(schema_str))
