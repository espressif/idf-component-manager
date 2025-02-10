# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json
import os
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest
from click.testing import CliRunner
from jsonschema.exceptions import ValidationError

from idf_component_manager.cli.core import initialize_cli
from idf_component_manager.core import ComponentManager
from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.manager import ManifestManager
from tests.network_test_utils import use_vcr_or_real_env


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_manifest_create_add_dependency.yaml')
@pytest.mark.network
def test_manifest_create_add_dependency(mock_registry):  # noqa: ARG001
    runner = CliRunner()
    with runner.isolated_filesystem() as tempdir:
        Path(tempdir, 'main').mkdir(parents=True, exist_ok=True)
        Path(tempdir, 'components', 'foo').mkdir(parents=True, exist_ok=True)
        Path(tempdir, 'src').mkdir(parents=True, exist_ok=True)
        main_manifest_path = Path(tempdir, 'main', MANIFEST_FILENAME)
        foo_manifest_path = Path(tempdir, 'components', 'foo', MANIFEST_FILENAME)
        # realpath fix for macos: /var is a symlink to /private/var
        # https://stackoverflow.com/questions/12482702/pythons-os-chdir-and-os-getcwd-mismatch-when-using-tempfile-mkdtemp-on-ma
        src_path = Path(tempdir, 'src').resolve()
        src_manifest_path = src_path / MANIFEST_FILENAME

        cli = initialize_cli()

        assert 'Created' in runner.invoke(cli, ['manifest', 'create']).output
        assert 'Created' in runner.invoke(cli, ['manifest', 'create', '--component', 'foo']).output
        assert 'Created' in runner.invoke(cli, ['manifest', 'create', '--path', src_path]).output

        assert (
            runner.invoke(
                cli, ['manifest', 'create', '--component', 'src', '--path', src_path]
            ).exit_code
            == 1
        )
        for filepath in [main_manifest_path, foo_manifest_path]:
            with open(filepath) as file:
                assert file.readline().startswith('## IDF Component Manager')

        assert (
            'Successfully added dependency'
            in runner.invoke(
                cli, ['manifest', 'add-dependency', 'test_component_manager/cmp']
            ).output
        )
        manifest_manager = ManifestManager(main_manifest_path, 'main')
        assert manifest_manager.manifest_tree['dependencies']['test_component_manager/cmp'] == '*'
        assert (
            'Successfully added dependency'
            in runner.invoke(
                cli,
                ['manifest', 'add-dependency', 'test_component_manager/cmp', '--component', 'foo'],
            ).output
        )
        manifest_manager = ManifestManager(foo_manifest_path, 'foo')
        assert manifest_manager.manifest_tree['dependencies']['test_component_manager/cmp'] == '*'
        assert (
            'Successfully added dependency'
            in runner.invoke(
                cli,
                ['manifest', 'add-dependency', 'test_component_manager/cmp', '--path', src_path],
            ).output
        )
        manifest_manager = ManifestManager(src_manifest_path, 'src')
        assert manifest_manager.manifest_tree['dependencies']['test_component_manager/cmp'] == '*'


def test_manifest_schema(tmp_path, valid_manifest):
    tempdir = str(tmp_path)

    runner = CliRunner()
    with runner.isolated_filesystem(tempdir) as tempdir:
        output = runner.invoke(initialize_cli(), ['manifest', 'schema']).output
        schema_dict = json.loads(output)
        valid_manifest['dependencies']['test']['rules'] = [{'if': 'idf_version < 5'}]
        jsonschema.validate(valid_manifest, schema_dict)

        with pytest.raises(ValidationError, match=r"\[\{'if': 'foo < 5'}]"):
            invalid_manifest = deepcopy(valid_manifest)['dependencies']['test']['rules'] = [
                {'if': 'foo < 5'}
            ]
            jsonschema.validate(invalid_manifest, schema_dict)

        with pytest.raises(ValidationError, match=r'\[1, 2, 3]'):
            invalid_manifest = deepcopy(valid_manifest)['dependencies']['test']['version'] = [
                1,
                2,
                3,
            ]
            jsonschema.validate(invalid_manifest, schema_dict)

        with pytest.raises(ValidationError, match=r"'1.2.3.pre.1'"):
            invalid_manifest = deepcopy(valid_manifest)['version'] = '1.2.3.pre.1'
            jsonschema.validate(invalid_manifest, schema_dict)

        with pytest.raises(ValidationError, match=r"'test.me'"):
            invalid_manifest = deepcopy(valid_manifest)['url'] = 'test.me'
            jsonschema.validate(invalid_manifest, schema_dict)


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_add_dependency_with_registry_url.yaml')
@pytest.mark.network
def test_add_dependency_with_registry_url(mock_registry):  # noqa: ARG001
    registry_url = os.getenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:5000')
    runner = CliRunner()
    with runner.isolated_filesystem() as tempdir:
        main_path = Path(tempdir) / 'main'
        main_path.mkdir(parents=True, exist_ok=True)
        manager = ComponentManager(path=str(tempdir))
        manager.create_manifest()

        assert (
            'Successfully added dependency'
            in runner.invoke(
                initialize_cli(),
                [
                    'manifest',
                    'add-dependency',
                    'test_component_manager/cmp==1.0.0',
                    '--registry-url',
                    registry_url,
                ],
            ).output
        )

        assert (
            f'registry_url: {registry_url}'
            in Path(tempdir, 'main', 'idf_component.yml').read_text()
        )


def test_add_git_dependency():
    runner = CliRunner()
    with runner.isolated_filesystem() as tempdir:
        cli = initialize_cli()
        main_path = Path(tempdir) / 'main'
        main_path.mkdir(parents=True, exist_ok=True)
        manager = ComponentManager(path=str(tempdir))
        manager.create_manifest()

        result = runner.invoke(
            cli,
            [
                'manifest',
                'add-dependency',
                'jozef',
                '--git',
                'https://github.com/espressif/example_components.git',
            ],
        ).output
        assert 'Successfully' in result

        assert (
            'git: https://github.com/espressif/example_components.git'
            in Path(tempdir, 'main', 'idf_component.yml').read_text()
        )

        result = runner.invoke(
            cli,
            [
                'manifest',
                'add-dependency',
                'jozef1',
                '--git',
                'https://github.com/espressif/example_components.git',
                '--git-path',
                'cmp',
            ],
        ).output

        assert 'Successfully' in result

        assert 'path: cmp' in Path(tempdir, 'main', 'idf_component.yml').read_text()

        assert (
            'Successfully'
            in runner.invoke(
                cli,
                [
                    'manifest',
                    'add-dependency',
                    'jozef2',
                    '--git',
                    'https://github.com/espressif/example_components.git',
                    '--git-ref',
                    # pragma: allowlist nextline secret
                    '6a7f7591fa4bf663f44fe27c1515c03f86012021',
                ],
            ).output
        )

        assert (
            # pragma: allowlist nextline secret
            'version: 6a7f7591fa4bf663f44fe27c1515c03f86012021'
            in Path(tempdir, 'main', 'idf_component.yml').read_text()
        )

        assert (
            'Successfully'
            in runner.invoke(
                cli,
                [
                    'manifest',
                    'add-dependency',
                    'jozef3',
                    '--git',
                    'https://github.com/espressif/example_components.git',
                    '--git-ref',
                    'feature/add_git_component',
                ],
            ).output
        )

        assert (
            'version: feature/add_git_component'
            in Path(tempdir, 'main', 'idf_component.yml').read_text()
        )


def test_add_git_dependency_invalid():
    runner = CliRunner()
    with runner.isolated_filesystem() as tempdir:
        cli = initialize_cli()
        main_path = Path(tempdir) / 'main'
        main_path.mkdir(parents=True, exist_ok=True)
        manager = ComponentManager(path=str(tempdir))
        manager.create_manifest()

        output = runner.invoke(
            cli,
            [
                'manifest',
                'add-dependency',
                'jozef',
                '--git',
                'https://github.com/espressif/example_compnents.git',
            ],
        ).exception

        assert (
            'Repository "https://github.com/espressif/example_compnents.git" does not exist'
            in str(output)
        )

        output = runner.invoke(
            cli,
            [
                'manifest',
                'add-dependency',
                'jozef',
                '--git',
                'https://github.com/espressif/example_components.git',
                '--git-path',
                'ciempi',
            ],
        ).exception
        assert 'Path "ciempi" does not exist' in str(output)

        output = runner.invoke(
            cli,
            [
                'manifest',
                'add-dependency',
                'jozef',
                '--git',
                'https://github.com/espressif/example_components.git',
                '--git-ref',
                'trest',
            ],
        ).exception
        assert 'Git reference "trest" does not exist' in str(output)


def test_manifest_keeps_comments():
    runner = CliRunner()
    with runner.isolated_filesystem() as tempdir:
        main_path = Path(tempdir) / 'main'
        main_path.mkdir(parents=True, exist_ok=True)
        manifest_path = main_path / MANIFEST_FILENAME
        previous_content = (
            "# Comment 1\ndependencies:\n    # Comment 2\n    espressif/cmp: '*'\n# Comment 3\n"
        )
        manifest_path.write_text(previous_content)

        output = runner.invoke(
            initialize_cli(),
            [
                'manifest',
                'add-dependency',
                'jozef',
                '--git',
                'https://github.com/espressif/example_components.git',
            ],
        )

        # Check that the command was successful (manifest modified)
        assert output.exit_code == 0

        updated_content = manifest_path.read_text()
        assert all(
            comment in updated_content for comment in ['# Comment 1', '# Comment 2', '# Comment 3']
        )
